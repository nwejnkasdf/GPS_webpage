from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from auth import require_admin_api
from database import get_db
from models.announcement import Announcement
from schemas.announcement import AnnouncementCreate, AnnouncementRead, AnnouncementUpdate

router = APIRouter()


@router.get("/announcements", response_model=list[AnnouncementRead])
def list_announcements(db: Session = Depends(get_db)):
    return (
        db.query(Announcement)
        .order_by(Announcement.is_pinned.desc(), Announcement.created_at.desc())
        .all()
    )


@router.post("/announcements", response_model=AnnouncementRead, status_code=201, dependencies=[Depends(require_admin_api)])
def create_announcement(data: AnnouncementCreate, db: Session = Depends(get_db)):
    announcement = Announcement(**data.model_dump())
    db.add(announcement)
    db.commit()
    db.refresh(announcement)
    return announcement


@router.get("/announcements/{announcement_id}", response_model=AnnouncementRead)
def get_announcement(announcement_id: int, db: Session = Depends(get_db)):
    announcement = db.query(Announcement).filter(Announcement.id == announcement_id).first()
    if not announcement:
        raise HTTPException(status_code=404, detail="공지를 찾을 수 없습니다.")
    return announcement


@router.put("/announcements/{announcement_id}", response_model=AnnouncementRead, dependencies=[Depends(require_admin_api)])
def update_announcement(announcement_id: int, data: AnnouncementUpdate, db: Session = Depends(get_db)):
    announcement = db.query(Announcement).filter(Announcement.id == announcement_id).first()
    if not announcement:
        raise HTTPException(status_code=404, detail="공지를 찾을 수 없습니다.")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(announcement, field, value)
    db.commit()
    db.refresh(announcement)
    return announcement


@router.delete("/announcements/{announcement_id}", status_code=204, dependencies=[Depends(require_admin_api)])
def delete_announcement(announcement_id: int, db: Session = Depends(get_db)):
    announcement = db.query(Announcement).filter(Announcement.id == announcement_id).first()
    if not announcement:
        raise HTTPException(status_code=404, detail="공지를 찾을 수 없습니다.")
    db.delete(announcement)
    db.commit()
