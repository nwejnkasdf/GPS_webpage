import asyncio
from datetime import datetime, time

from sqlalchemy.orm import Session as DBSession

from crawlers.boj_scraper import BOJScrapingError, was_solved_before_deadline
from crawlers.solved_ac import is_gold_or_higher
from models.attendance import Attendance
from models.member import Member
from models.session import Session as SessionModel
from models.week import CriteriaMode, Week
from models.week_problem import WeekProblem


def _compute_is_present(
    week: Week,
    solved_gold: int,
    solved_total: int,
) -> bool:
    gold_ok = solved_gold >= week.min_gold_problems
    total_ok = solved_total >= week.min_total_problems
    if week.criteria_mode == CriteriaMode.AND:
        return gold_ok and total_ok
    else:  # OR
        return gold_ok or total_ok


def _upsert_attendance(
    db: DBSession,
    member_id: int,
    week_id: int,
    is_present: bool,
    solved_gold: int,
    solved_total: int,
) -> Attendance:
    att = (
        db.query(Attendance)
        .filter_by(member_id=member_id, week_id=week_id)
        .first()
    )
    if att is None:
        att = Attendance(member_id=member_id, week_id=week_id)
        db.add(att)

    att.is_present = is_present
    att.solved_gold_count = solved_gold
    att.solved_total_count = solved_total
    att.last_checked = datetime.utcnow()
    db.commit()
    db.refresh(att)
    return att


async def check_member_week(
    member: Member,
    week: Week,
    problems: list[WeekProblem],
    deadline: datetime,
) -> tuple[int, int, list[str]]:
    """
    Returns (solved_gold, solved_total, errors) for one member in one week.
    Checks all problems sequentially (to respect rate limiter).
    """
    solved_gold = 0
    solved_total = 0
    errors = []

    for problem in problems:
        try:
            solved = await was_solved_before_deadline(
                user_id=member.baekjoon_handle,
                problem_id=problem.problem_number,
                deadline=deadline,
            )
            if solved:
                solved_total += 1
                if is_gold_or_higher(problem.difficulty):
                    solved_gold += 1
        except BOJScrapingError as e:
            errors.append(f"[{member.baekjoon_handle}] 문제 {problem.problem_number}: {e}")
        except Exception as e:
            errors.append(
                f"[{member.baekjoon_handle}] 문제 {problem.problem_number}: 알 수 없는 오류 - {e}"
            )

    return solved_gold, solved_total, errors


async def check_session_attendance(
    db: DBSession,
    session_id: int,
    task_store: dict,
    task_id: str,
) -> None:
    """
    Full attendance check for a session. Updates task_store for progress polling.
    Weeks: sequential. Members per week: concurrent.
    """
    session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
    if not session:
        task_store[task_id] = {"status": "error", "progress": 0, "total": 0,
                               "errors": ["세션을 찾을 수 없습니다."]}
        return

    members = session.members
    weeks = session.weeks

    total = len(members) * len(weeks)
    task_store[task_id].update({"status": "running", "progress": 0, "total": total, "errors": []})

    done = 0
    for week in weeks:
        deadline = datetime.combine(week.end_date, time(23, 59, 59))
        problems: list[WeekProblem] = week.problems

        if not problems:
            # 문제가 없는 주차는 스킵
            done += len(members)
            task_store[task_id]["progress"] = done
            continue

        async def process_member(member: Member):
            sg, st, errs = await check_member_week(member, week, problems, deadline)
            is_present = _compute_is_present(week, sg, st)
            _upsert_attendance(db, member.id, week.id, is_present, sg, st)
            return errs

        results = await asyncio.gather(
            *[process_member(m) for m in members],
            return_exceptions=True,
        )

        for result in results:
            if isinstance(result, Exception):
                task_store[task_id]["errors"].append(str(result))
            elif isinstance(result, list):
                task_store[task_id]["errors"].extend(result)
            done += 1
            task_store[task_id]["progress"] = done

    task_store[task_id]["status"] = "done"


async def check_week_attendance(
    db: DBSession,
    week_id: int,
    task_store: dict,
    task_id: str,
) -> None:
    """Single-week attendance check."""
    week = db.query(Week).filter(Week.id == week_id).first()
    if not week:
        task_store[task_id] = {"status": "error", "progress": 0, "total": 0,
                               "errors": ["주차를 찾을 수 없습니다."]}
        return

    session = db.query(SessionModel).filter(SessionModel.id == week.session_id).first()
    members = session.members
    problems = week.problems
    deadline = datetime.combine(week.end_date, time(23, 59, 59))

    total = len(members)
    task_store[task_id].update({"status": "running", "progress": 0, "total": total, "errors": []})

    for i, member in enumerate(members):
        sg, st, errs = await check_member_week(member, week, problems, deadline)
        is_present = _compute_is_present(week, sg, st)
        _upsert_attendance(db, member.id, week.id, is_present, sg, st)
        task_store[task_id]["errors"].extend(errs)
        task_store[task_id]["progress"] = i + 1

    task_store[task_id]["status"] = "done"
