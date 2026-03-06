import random
from datetime import datetime

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from auth import require_admin_api
from database import get_db
from models.boj_game import BojGameProblem, BojGameRound, BojGameRoundProblem
from models.telepathy import TelepathyOption, TelepathyRound, TelepathySubmission, TelepathyTeam
from schemas.recreation import (
    BojRoundCreate,
    TelepathyRoundCreate,
    TelepathyRoundUpdate,
    TelepathyTeamsUpdate,
)
from services.recreation_service import build_boj_state, build_telepathy_state, ensure_default_telepathy_teams

router = APIRouter()


def _get_telepathy_round_or_404(round_id: int, db: Session) -> TelepathyRound:
    round_obj = db.query(TelepathyRound).filter(TelepathyRound.id == round_id).first()
    if not round_obj:
        raise HTTPException(status_code=404, detail="텔레파시 라운드를 찾을 수 없습니다.")
    return round_obj


def _get_telepathy_option_or_404(option_id: int, db: Session) -> TelepathyOption:
    option = db.query(TelepathyOption).filter(TelepathyOption.id == option_id).first()
    if not option:
        raise HTTPException(status_code=404, detail="텔레파시 선택지를 찾을 수 없습니다.")
    return option


def _get_boj_problem_or_404(problem_id: int, db: Session) -> BojGameProblem:
    problem = db.query(BojGameProblem).filter(BojGameProblem.id == problem_id).first()
    if not problem:
        raise HTTPException(status_code=404, detail="문제 풀 항목을 찾을 수 없습니다.")
    return problem


def _get_boj_round_or_404(round_id: int, db: Session) -> BojGameRound:
    round_obj = db.query(BojGameRound).filter(BojGameRound.id == round_id).first()
    if not round_obj:
        raise HTTPException(status_code=404, detail="백준 게임 라운드를 찾을 수 없습니다.")
    return round_obj


@router.get("/recreation/telepathy/admin/state", dependencies=[Depends(require_admin_api)])
def get_telepathy_admin_state(db: Session = Depends(get_db)):
    return build_telepathy_state(db)


@router.put("/recreation/telepathy/teams", dependencies=[Depends(require_admin_api)])
def update_telepathy_teams(payload: TelepathyTeamsUpdate, db: Session = Depends(get_db)):
    ensure_default_telepathy_teams(db)
    teams = {team.id: team for team in db.query(TelepathyTeam).all()}
    for item in payload.teams:
        team = teams.get(item.id)
        if team is None:
            raise HTTPException(status_code=404, detail=f"{item.id}번 조를 찾을 수 없습니다.")
        team_name = item.name.strip()
        if not team_name:
            raise HTTPException(status_code=400, detail="조 이름은 비워둘 수 없습니다.")
        team.name = team_name
    db.commit()
    return build_telepathy_state(db)


@router.post("/recreation/telepathy/rounds", dependencies=[Depends(require_admin_api)])
def create_telepathy_round(payload: TelepathyRoundCreate, db: Session = Depends(get_db)):
    title = payload.title.strip()
    if not title:
        raise HTTPException(status_code=400, detail="라운드 제목을 입력해 주세요.")
    round_obj = TelepathyRound(
        title=title,
        prompt=payload.prompt.strip(),
    )
    db.add(round_obj)
    db.commit()
    return build_telepathy_state(db)


@router.put("/recreation/telepathy/rounds/{round_id}", dependencies=[Depends(require_admin_api)])
def update_telepathy_round(round_id: int, payload: TelepathyRoundUpdate, db: Session = Depends(get_db)):
    round_obj = _get_telepathy_round_or_404(round_id, db)
    if payload.title is not None:
        title = payload.title.strip()
        if not title:
            raise HTTPException(status_code=400, detail="라운드 제목을 입력해 주세요.")
        round_obj.title = title
    if payload.prompt is not None:
        round_obj.prompt = payload.prompt.strip()
    db.commit()
    return build_telepathy_state(db)


@router.delete("/recreation/telepathy/rounds/{round_id}", dependencies=[Depends(require_admin_api)])
def delete_telepathy_round(round_id: int, db: Session = Depends(get_db)):
    round_obj = _get_telepathy_round_or_404(round_id, db)
    db.delete(round_obj)
    db.commit()
    return {"ok": True}


@router.post("/recreation/telepathy/rounds/{round_id}/options", dependencies=[Depends(require_admin_api)])
async def create_telepathy_option(
    round_id: int,
    name: str = Form(...),
    image_url: str = Form(""),
    image_file: UploadFile | None = File(default=None),
    db: Session = Depends(get_db),
):
    round_obj = _get_telepathy_round_or_404(round_id, db)
    option_name = name.strip()
    if not option_name:
        raise HTTPException(status_code=400, detail="선택지 이름을 입력해 주세요.")

    next_display_order = max((option.display_order for option in round_obj.options), default=0) + 1

    image_data = None
    image_content_type = None
    if image_file is not None and image_file.filename:
        image_data = await image_file.read()
        image_content_type = image_file.content_type or "application/octet-stream"

    option = TelepathyOption(
        round_id=round_id,
        name=option_name,
        image_url=image_url.strip() or None,
        image_data=image_data,
        image_content_type=image_content_type,
        display_order=next_display_order,
    )
    db.add(option)
    db.commit()
    return build_telepathy_state(db)


@router.delete("/recreation/telepathy/options/{option_id}", dependencies=[Depends(require_admin_api)])
def delete_telepathy_option(option_id: int, db: Session = Depends(get_db)):
    option = _get_telepathy_option_or_404(option_id, db)
    db.delete(option)
    db.commit()
    return {"ok": True}


@router.post("/recreation/telepathy/rounds/{round_id}/activate", dependencies=[Depends(require_admin_api)])
def activate_telepathy_round(round_id: int, db: Session = Depends(get_db)):
    round_obj = _get_telepathy_round_or_404(round_id, db)
    if len(round_obj.options) < 2:
        raise HTTPException(status_code=400, detail="선택지는 최소 2개 이상이어야 합니다.")

    rounds = db.query(TelepathyRound).all()
    for item in rounds:
        item.is_active = item.id == round_id
        if item.id == round_id:
            item.is_revealed = False
    db.commit()
    return build_telepathy_state(db)


@router.post("/recreation/telepathy/rounds/{round_id}/reveal", dependencies=[Depends(require_admin_api)])
def reveal_telepathy_round(round_id: int, db: Session = Depends(get_db)):
    round_obj = _get_telepathy_round_or_404(round_id, db)
    round_obj.is_active = False
    round_obj.is_revealed = True
    db.commit()
    return build_telepathy_state(db)


@router.post("/recreation/telepathy/rounds/{round_id}/reset", dependencies=[Depends(require_admin_api)])
def reset_telepathy_round(round_id: int, db: Session = Depends(get_db)):
    round_obj = _get_telepathy_round_or_404(round_id, db)
    (
        db.query(TelepathySubmission)
        .filter(TelepathySubmission.round_id == round_id)
        .delete(synchronize_session=False)
    )
    round_obj.is_active = False
    round_obj.is_revealed = False
    db.commit()
    return build_telepathy_state(db)


@router.get("/recreation/boj/admin/state", dependencies=[Depends(require_admin_api)])
def get_boj_admin_state(db: Session = Depends(get_db)):
    return build_boj_state(db)


@router.post("/recreation/boj/problems", dependencies=[Depends(require_admin_api)])
async def create_boj_problem(
    problem_number: int = Form(...),
    difficulty: int = Form(...),
    title: str = Form(""),
    image_file: UploadFile | None = File(default=None),
    db: Session = Depends(get_db),
):
    if difficulty < 1 or difficulty > 30:
        raise HTTPException(status_code=400, detail="난이도는 1부터 30 사이여야 합니다.")

    existing = (
        db.query(BojGameProblem)
        .filter(BojGameProblem.problem_number == problem_number)
        .first()
    )
    if existing:
        raise HTTPException(status_code=409, detail="이미 등록된 문제 번호입니다.")

    image_data = None
    image_content_type = None
    if image_file is not None and image_file.filename:
        image_data = await image_file.read()
        image_content_type = image_file.content_type or "application/octet-stream"

    problem = BojGameProblem(
        problem_number=problem_number,
        title=title.strip(),
        difficulty=difficulty,
        image_data=image_data,
        image_content_type=image_content_type,
    )
    db.add(problem)
    db.commit()
    return build_boj_state(db)


@router.delete("/recreation/boj/problems/{problem_id}", dependencies=[Depends(require_admin_api)])
def delete_boj_problem(problem_id: int, db: Session = Depends(get_db)):
    problem = _get_boj_problem_or_404(problem_id, db)
    db.delete(problem)
    db.commit()
    return {"ok": True}


@router.post("/recreation/boj/rounds", dependencies=[Depends(require_admin_api)])
def create_boj_round(payload: BojRoundCreate, db: Session = Depends(get_db)):
    pool_problems = db.query(BojGameProblem).all()
    if len(pool_problems) < payload.problem_count:
        raise HTTPException(status_code=400, detail="문제 풀이 부족합니다. 먼저 문제를 더 등록해 주세요.")

    for round_obj in db.query(BojGameRound).all():
        round_obj.is_active = False

    round_count = db.query(BojGameRound).count() + 1
    title = (payload.title or "").strip() or f"백준 라운드 {round_count}"
    round_obj = BojGameRound(
        title=title,
        is_active=True,
        last_result_status="pending",
    )
    db.add(round_obj)
    db.flush()

    selected_problems = random.sample(pool_problems, payload.problem_count)
    shuffled_problems = selected_problems[:]
    random.shuffle(shuffled_problems)

    for display_order, pool_problem in enumerate(shuffled_problems, start=1):
        db.add(
            BojGameRoundProblem(
                round_id=round_obj.id,
                problem_number=pool_problem.problem_number,
                title=pool_problem.title,
                difficulty=pool_problem.difficulty,
                image_data=pool_problem.image_data,
                image_content_type=pool_problem.image_content_type,
                display_order=display_order,
            )
        )

    db.commit()
    return build_boj_state(db)


@router.post("/recreation/boj/rounds/{round_id}/activate", dependencies=[Depends(require_admin_api)])
def activate_boj_round(round_id: int, db: Session = Depends(get_db)):
    _get_boj_round_or_404(round_id, db)
    for round_obj in db.query(BojGameRound).all():
        round_obj.is_active = round_obj.id == round_id
    db.commit()
    return build_boj_state(db)


@router.post("/recreation/boj/rounds/{round_id}/reset", dependencies=[Depends(require_admin_api)])
def reset_boj_round(round_id: int, db: Session = Depends(get_db)):
    round_obj = _get_boj_round_or_404(round_id, db)
    shuffled_problems = list(round_obj.problems)
    random.shuffle(shuffled_problems)
    for display_order, problem in enumerate(shuffled_problems, start=1):
        problem.display_order = display_order

    round_obj.last_result_status = "pending"
    round_obj.last_submitted_order = None
    round_obj.last_attempt_at = None
    db.commit()
    return build_boj_state(db)


@router.delete("/recreation/boj/rounds/{round_id}", dependencies=[Depends(require_admin_api)])
def delete_boj_round(round_id: int, db: Session = Depends(get_db)):
    round_obj = _get_boj_round_or_404(round_id, db)
    db.delete(round_obj)
    db.commit()
    return {"ok": True}
