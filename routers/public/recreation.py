from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.orm import Session

from database import get_db
from models.boj_game import BojGameConfig, BojGameCurrentProblem, BojGameProblem
from models.telepathy import (
    TelepathyOption,
    TelepathyRound,
    TelepathySubmission,
    TelepathySubmissionRole,
    TelepathyTeam,
)
from schemas.recreation import BojSubmitRequest, TelepathySubmissionCreate
from services.recreation_service import (
    build_boj_state,
    build_telepathy_state,
    ensure_boj_current_set,
    ensure_default_boj_config,
    ensure_default_telepathy_teams,
    regenerate_boj_current_set,
    serialize_telepathy_round,
    sort_telepathy_teams,
)

router = APIRouter()


def _get_active_telepathy_round(db: Session) -> TelepathyRound | None:
    return (
        db.query(TelepathyRound)
        .filter(TelepathyRound.is_active.is_(True))
        .order_by(TelepathyRound.updated_at.desc(), TelepathyRound.id.desc())
        .first()
    )


def _get_boj_config(db: Session) -> BojGameConfig:
    return ensure_default_boj_config(db)


def _role_from_path(role: str) -> TelepathySubmissionRole:
    try:
        return TelepathySubmissionRole(role)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="역할은 representative 또는 team 이어야 합니다.") from exc


@router.get("/public/recreation/telepathy/current")
def get_current_telepathy_round(
    team_id: int | None = None,
    role: str | None = None,
    db: Session = Depends(get_db),
):
    ensure_default_telepathy_teams(db)
    teams = sort_telepathy_teams(db.query(TelepathyTeam).all())
    active_round = _get_active_telepathy_round(db)
    payload = {
        "teams": [{"id": team.id, "name": team.name, "display_order": team.display_order} for team in teams],
        "active_round": serialize_telepathy_round(active_round, teams) if active_round else None,
        "submission": None,
    }

    if active_round and team_id and role:
        role_enum = _role_from_path(role)
        submission = (
            db.query(TelepathySubmission)
            .filter(
                TelepathySubmission.round_id == active_round.id,
                TelepathySubmission.team_id == team_id,
                TelepathySubmission.role == role_enum,
            )
            .first()
        )
        if submission:
            payload["submission"] = {
                "updated_at": submission.updated_at.isoformat(),
                "ranking": submission.ranking or [],
            }

    return payload


@router.post("/public/recreation/telepathy/submissions/{role}")
def submit_telepathy_ranking(
    role: str,
    payload: TelepathySubmissionCreate,
    db: Session = Depends(get_db),
):
    ensure_default_telepathy_teams(db)
    role_enum = _role_from_path(role)

    active_round = _get_active_telepathy_round(db)
    if active_round is None:
        raise HTTPException(status_code=404, detail="현재 진행 중인 텔레파시 라운드가 없습니다.")

    team = db.query(TelepathyTeam).filter(TelepathyTeam.id == payload.team_id).first()
    if team is None:
        raise HTTPException(status_code=404, detail="조 정보를 찾을 수 없습니다.")

    option_ids = {option.id for option in active_round.options}
    submitted_ids = payload.ranking
    if len(submitted_ids) != len(option_ids) or set(submitted_ids) != option_ids:
        raise HTTPException(status_code=400, detail="모든 선택지를 한 번씩 순위에 넣어야 합니다.")

    submission = (
        db.query(TelepathySubmission)
        .filter(
            TelepathySubmission.round_id == active_round.id,
            TelepathySubmission.team_id == payload.team_id,
            TelepathySubmission.role == role_enum,
        )
        .first()
    )
    if submission is None:
        submission = TelepathySubmission(
            round_id=active_round.id,
            team_id=payload.team_id,
            role=role_enum,
        )
        db.add(submission)

    submission.ranking = submitted_ids
    submission.updated_at = datetime.utcnow()
    db.commit()

    return {
        "ok": True,
        "updated_at": submission.updated_at.isoformat(),
        "round_id": active_round.id,
    }


@router.get("/public/recreation/telepathy/display")
def get_telepathy_display_state(db: Session = Depends(get_db)):
    return build_telepathy_state(db)


@router.get("/public/recreation/telepathy/options/{option_id}/image")
def get_telepathy_option_image(option_id: int, db: Session = Depends(get_db)):
    option = db.query(TelepathyOption).filter(TelepathyOption.id == option_id).first()
    if option is None or not option.image_data:
        raise HTTPException(status_code=404, detail="이미지를 찾을 수 없습니다.")
    return Response(content=option.image_data, media_type=option.image_content_type or "image/jpeg")


@router.get("/public/recreation/boj/current")
def get_current_boj_round(db: Session = Depends(get_db)):
    state = build_boj_state(db)
    return {
        "current_round": state["current_round"],
        "config": state["config"],
    }


@router.post("/public/recreation/boj/submit")
def submit_boj_round(payload: BojSubmitRequest, db: Session = Depends(get_db)):
    config = ensure_boj_current_set(db)
    current_problems = (
        db.query(BojGameCurrentProblem)
        .filter(BojGameCurrentProblem.config_id == config.id)
        .order_by(BojGameCurrentProblem.display_order, BojGameCurrentProblem.id)
        .all()
    )
    if not current_problems:
        raise HTTPException(status_code=404, detail="현재 진행 중인 문제 세트가 없습니다.")

    current_problem_ids = [problem.id for problem in current_problems]
    submitted_ids = payload.ordered_problem_ids
    if len(submitted_ids) != len(current_problem_ids) or set(submitted_ids) != set(current_problem_ids):
        raise HTTPException(status_code=400, detail="현재 세트의 모든 문제를 한 번씩 정렬해야 합니다.")

    difficulty_lookup = {problem.id: problem.pool_problem.difficulty for problem in current_problems}
    difficulties = [difficulty_lookup[problem_id] for problem_id in submitted_ids]
    is_correct = all(left <= right for left, right in zip(difficulties, difficulties[1:]))

    config.last_result_status = "passed" if is_correct else "failed"
    config.last_submitted_order = submitted_ids
    config.last_attempt_at = datetime.utcnow()
    db.commit()

    pool_count = db.query(BojGameProblem).count()
    if pool_count >= config.sample_size:
        config = regenerate_boj_current_set(db, config)

    next_state = build_boj_state(db)
    return {
        "is_correct": is_correct,
        "current_round": next_state["current_round"],
    }


@router.get("/public/recreation/boj/problems/{problem_id}/image")
def get_boj_problem_image(problem_id: int, db: Session = Depends(get_db)):
    problem = db.query(BojGameProblem).filter(BojGameProblem.id == problem_id).first()
    if problem is None or not problem.image_data:
        raise HTTPException(status_code=404, detail="이미지를 찾을 수 없습니다.")
    return Response(content=problem.image_data, media_type=problem.image_content_type or "image/jpeg")
