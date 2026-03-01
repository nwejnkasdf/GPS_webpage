from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from auth import require_admin_api
from crawlers.solved_ac import difficulty_label, difficulty_tier, fetch_problem_difficulty
from database import get_db
from models.session import Session as SessionModel
from models.week import Week
from models.week_problem import WeekProblem
from schemas.week import WeekCreate, WeekProblemRead, WeekRead, WeekUpdate

router = APIRouter()


def _get_session_or_404(session_id: int, db: Session) -> SessionModel:
    s = db.query(SessionModel).filter(SessionModel.id == session_id).first()
    if not s:
        raise HTTPException(status_code=404, detail="세션을 찾을 수 없습니다.")
    return s


def _get_week_or_404(week_id: int, db: Session) -> Week:
    w = db.query(Week).filter(Week.id == week_id).first()
    if not w:
        raise HTTPException(status_code=404, detail="주차를 찾을 수 없습니다.")
    return w


def _enrich_problem(p: WeekProblem) -> WeekProblemRead:
    return WeekProblemRead(
        id=p.id,
        week_id=p.week_id,
        problem_number=p.problem_number,
        difficulty=p.difficulty,
        difficulty_label=difficulty_label(p.difficulty),
        difficulty_tier=difficulty_tier(p.difficulty),
    )


def _enrich_week(w: Week) -> WeekRead:
    return WeekRead(
        id=w.id,
        session_id=w.session_id,
        week_number=w.week_number,
        end_date=w.end_date,
        min_gold_problems=w.min_gold_problems,
        min_total_problems=w.min_total_problems,
        criteria_mode=w.criteria_mode,
        problems=[_enrich_problem(p) for p in w.problems],
    )


@router.get("/sessions/{session_id}/weeks", response_model=list[WeekRead])
def list_weeks(session_id: int, db: Session = Depends(get_db)):
    _get_session_or_404(session_id, db)
    weeks = (
        db.query(Week)
        .filter(Week.session_id == session_id)
        .order_by(Week.week_number)
        .all()
    )
    return [_enrich_week(w) for w in weeks]


@router.post("/sessions/{session_id}/weeks", response_model=WeekRead, status_code=201, dependencies=[Depends(require_admin_api)])
def create_week(session_id: int, data: WeekCreate, db: Session = Depends(get_db)):
    _get_session_or_404(session_id, db)
    week = Week(session_id=session_id, **data.model_dump())
    db.add(week)
    db.commit()
    db.refresh(week)
    return _enrich_week(week)


@router.get("/weeks/{week_id}", response_model=WeekRead)
def get_week(week_id: int, db: Session = Depends(get_db)):
    return _enrich_week(_get_week_or_404(week_id, db))


@router.put("/weeks/{week_id}", response_model=WeekRead, dependencies=[Depends(require_admin_api)])
def update_week(week_id: int, data: WeekUpdate, db: Session = Depends(get_db)):
    week = _get_week_or_404(week_id, db)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(week, field, value)
    db.commit()
    db.refresh(week)
    return _enrich_week(week)


@router.delete("/weeks/{week_id}", status_code=204, dependencies=[Depends(require_admin_api)])
def delete_week(week_id: int, db: Session = Depends(get_db)):
    week = _get_week_or_404(week_id, db)
    db.delete(week)
    db.commit()


@router.get("/weeks/{week_id}/problems", response_model=list[WeekProblemRead])
def list_problems(week_id: int, db: Session = Depends(get_db)):
    _get_week_or_404(week_id, db)
    problems = db.query(WeekProblem).filter(WeekProblem.week_id == week_id).all()
    return [_enrich_problem(p) for p in problems]


@router.post("/weeks/{week_id}/problems", response_model=WeekProblemRead, status_code=201, dependencies=[Depends(require_admin_api)])
async def add_problem(week_id: int, problem_number: int, db: Session = Depends(get_db)):
    _get_week_or_404(week_id, db)

    # 중복 확인
    existing = (
        db.query(WeekProblem)
        .filter(WeekProblem.week_id == week_id, WeekProblem.problem_number == problem_number)
        .first()
    )
    if existing:
        raise HTTPException(status_code=409, detail="이미 추가된 문제입니다.")

    # solved.ac에서 난이도 조회
    difficulty = await fetch_problem_difficulty(problem_number)

    problem = WeekProblem(week_id=week_id, problem_number=problem_number, difficulty=difficulty)
    db.add(problem)
    db.commit()
    db.refresh(problem)
    return _enrich_problem(problem)


@router.post("/weeks/{week_id}/problems/bulk", status_code=200, dependencies=[Depends(require_admin_api)])
async def bulk_add_problems(week_id: int, problem_numbers: list[int], db: Session = Depends(get_db)):
    """
    여러 문제 번호를 한 번에 추가. 중복은 스킵.
    Returns: {"added": [...], "skipped": [...], "problems": [...enriched]}
    """
    _get_week_or_404(week_id, db)

    existing_nums = {
        p.problem_number
        for p in db.query(WeekProblem).filter(WeekProblem.week_id == week_id).all()
    }

    added = []
    skipped = []

    for num in problem_numbers:
        if num in existing_nums:
            skipped.append(num)
            continue
        difficulty = await fetch_problem_difficulty(num)
        p = WeekProblem(week_id=week_id, problem_number=num, difficulty=difficulty)
        db.add(p)
        existing_nums.add(num)
        added.append(num)

    db.commit()

    all_problems = db.query(WeekProblem).filter(WeekProblem.week_id == week_id).all()
    return {
        "added": added,
        "skipped": skipped,
        "problems": [_enrich_problem(p).model_dump() for p in all_problems],
    }


@router.post("/weeks/{week_id}/problems/refresh-difficulty", response_model=list[WeekProblemRead], dependencies=[Depends(require_admin_api)])
async def refresh_difficulty(week_id: int, db: Session = Depends(get_db)):
    """Re-fetch difficulty from solved.ac for all problems in this week."""
    _get_week_or_404(week_id, db)
    problems = db.query(WeekProblem).filter(WeekProblem.week_id == week_id).all()
    for p in problems:
        p.difficulty = await fetch_problem_difficulty(p.problem_number)
    db.commit()
    return [_enrich_problem(p) for p in problems]


@router.delete("/problems/{problem_id}", status_code=204, dependencies=[Depends(require_admin_api)])
def delete_problem(problem_id: int, db: Session = Depends(get_db)):
    problem = db.query(WeekProblem).filter(WeekProblem.id == problem_id).first()
    if not problem:
        raise HTTPException(status_code=404, detail="문제를 찾을 수 없습니다.")
    db.delete(problem)
    db.commit()
