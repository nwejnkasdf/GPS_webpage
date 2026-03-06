from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from auth import require_admin_api
from crawlers.solved_ac import fetch_problem_metadata
from database import get_db
from models.boj_game import BojGameConfig, BojGameCurrentProblem, BojGameProblem
from models.telepathy import TelepathyOption, TelepathyRound, TelepathySubmission, TelepathyTeam
from schemas.recreation import (
    BojConfigUpdate,
    TelepathyRoundCreate,
    TelepathyRoundUpdate,
    TelepathyTeamsUpdate,
)
from services.recreation_service import (
    build_boj_state,
    build_telepathy_state,
    ensure_boj_current_set,
    ensure_default_boj_config,
    ensure_default_telepathy_teams,
    regenerate_boj_current_set,
)

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


def _get_boj_config(db: Session) -> BojGameConfig:
    return ensure_default_boj_config(db)


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
    round_obj = TelepathyRound(title=title, prompt=payload.prompt.strip())
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
    title: str = Form(""),
    image_file: UploadFile | None = File(default=None),
    db: Session = Depends(get_db),
):
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

    metadata = await fetch_problem_metadata(problem_number)
    difficulty = int(metadata["difficulty"])
    if difficulty < 1 or difficulty > 30:
        raise HTTPException(
            status_code=400,
            detail="solved.ac에서 난이도를 가져오지 못했습니다. 문제 번호를 확인하거나 잠시 후 다시 시도해 주세요.",
        )

    title_text = title.strip() or str(metadata["title"]).strip()

    problem = BojGameProblem(
        problem_number=problem_number,
        title=title_text,
        difficulty=difficulty,
        image_data=image_data,
        image_content_type=image_content_type,
    )
    db.add(problem)
    db.commit()
    ensure_boj_current_set(db)
    return build_boj_state(db)


@router.delete("/recreation/boj/problems/{problem_id}", dependencies=[Depends(require_admin_api)])
def delete_boj_problem(problem_id: int, db: Session = Depends(get_db)):
    problem = _get_boj_problem_or_404(problem_id, db)
    config = _get_boj_config(db)
    was_in_current_set = (
        db.query(BojGameCurrentProblem)
        .filter(
            BojGameCurrentProblem.config_id == config.id,
            BojGameCurrentProblem.pool_problem_id == problem.id,
        )
        .count()
        > 0
    )

    if was_in_current_set:
        current_rows = (
            db.query(BojGameCurrentProblem)
            .filter(
                BojGameCurrentProblem.config_id == config.id,
                BojGameCurrentProblem.pool_problem_id == problem.id,
            )
            .all()
        )
        for current_row in current_rows:
            db.delete(current_row)

    db.delete(problem)
    db.commit()

    if was_in_current_set:
        regenerate_boj_current_set(db, config)

    return build_boj_state(db)


@router.put("/recreation/boj/config", dependencies=[Depends(require_admin_api)])
def update_boj_config(payload: BojConfigUpdate, db: Session = Depends(get_db)):
    config = _get_boj_config(db)
    config.sample_size = payload.sample_size
    config.last_result_status = "pending"
    config.last_submitted_order = None
    config.last_attempt_at = None
    db.commit()
    regenerate_boj_current_set(db, config)
    return build_boj_state(db)


@router.post("/recreation/boj/next-set", dependencies=[Depends(require_admin_api)])
def advance_boj_set(db: Session = Depends(get_db)):
    config = _get_boj_config(db)
    pool_count = db.query(BojGameProblem).count()
    if pool_count < config.sample_size:
        raise HTTPException(
            status_code=400,
            detail="문제풀 수가 샘플 개수보다 적습니다. 문제를 더 등록하거나 개수를 줄여 주세요.",
        )

    config.last_result_status = "pending"
    config.last_submitted_order = None
    config.last_attempt_at = None
    db.commit()
    regenerate_boj_current_set(db, config)
    return build_boj_state(db)
