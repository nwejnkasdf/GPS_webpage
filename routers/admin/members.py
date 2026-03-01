from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from auth import require_admin_api
from database import get_db
from models.member import Member
from models.session import Session as SessionModel
from schemas.member import MemberBulkItem, MemberCreate, MemberRead, MemberUpdate

router = APIRouter()


def _get_session_or_404(session_id: int, db: Session) -> SessionModel:
    s = db.query(SessionModel).filter(SessionModel.id == session_id).first()
    if not s:
        raise HTTPException(status_code=404, detail="세션을 찾을 수 없습니다.")
    return s


@router.get("/sessions/{session_id}/members", response_model=list[MemberRead])
def list_members(session_id: int, db: Session = Depends(get_db)):
    _get_session_or_404(session_id, db)
    return db.query(Member).filter(Member.session_id == session_id).all()


@router.post("/sessions/{session_id}/members", response_model=MemberRead, status_code=201, dependencies=[Depends(require_admin_api)])
def add_member(session_id: int, data: MemberCreate, db: Session = Depends(get_db)):
    _get_session_or_404(session_id, db)
    member = Member(session_id=session_id, **data.model_dump())
    db.add(member)
    db.commit()
    db.refresh(member)
    return member


@router.post("/sessions/{session_id}/members/bulk", response_model=list[MemberRead], status_code=201, dependencies=[Depends(require_admin_api)])
def bulk_add_members(session_id: int, data: list[MemberBulkItem], db: Session = Depends(get_db)):
    _get_session_or_404(session_id, db)
    members = [Member(session_id=session_id, **item.model_dump()) for item in data]
    db.add_all(members)
    db.commit()
    for m in members:
        db.refresh(m)
    return members


@router.put("/members/{member_id}", response_model=MemberRead, dependencies=[Depends(require_admin_api)])
def update_member(member_id: int, data: MemberUpdate, db: Session = Depends(get_db)):
    member = db.query(Member).filter(Member.id == member_id).first()
    if not member:
        raise HTTPException(status_code=404, detail="멤버를 찾을 수 없습니다.")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(member, field, value)
    db.commit()
    db.refresh(member)
    return member


@router.delete("/members/{member_id}", status_code=204, dependencies=[Depends(require_admin_api)])
def delete_member(member_id: int, db: Session = Depends(get_db)):
    member = db.query(Member).filter(Member.id == member_id).first()
    if not member:
        raise HTTPException(status_code=404, detail="멤버를 찾을 수 없습니다.")
    db.delete(member)
    db.commit()
