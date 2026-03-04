from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from auth import require_admin_api
from database import get_db
from models.club_info import ClubInfo
from schemas.club_info import ClubInfoRead, ClubInfoUpdate

router = APIRouter()


def _get_club_info(db: Session) -> ClubInfo:
    info = db.query(ClubInfo).first()
    if not info:
        raise HTTPException(status_code=404, detail="동아리 정보를 찾을 수 없습니다.")
    return info


@router.get("/club-info", response_model=ClubInfoRead)
def get_club_info(db: Session = Depends(get_db)):
    return _get_club_info(db)


@router.put("/club-info", response_model=ClubInfoRead, dependencies=[Depends(require_admin_api)])
def update_club_info(data: ClubInfoUpdate, db: Session = Depends(get_db)):
    info = _get_club_info(db)
    info.intro_text = data.intro_text
    db.commit()
    db.refresh(info)
    return info
