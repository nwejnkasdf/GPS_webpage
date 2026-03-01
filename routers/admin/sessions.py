from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from auth import require_admin_api
from database import get_db
from models.session import Session as SessionModel
from schemas.session import SessionCreate, SessionRead, SessionUpdate

router = APIRouter()


@router.get("/sessions", response_model=list[SessionRead])
def list_sessions(db: Session = Depends(get_db)):
    sessions = db.query(SessionModel).order_by(SessionModel.start_date.desc()).all()
    result = []
    for s in sessions:
        r = SessionRead(
            id=s.id,
            name=s.name,
            type=s.type,
            start_date=s.start_date,
            end_date=s.end_date,
            member_count=len(s.members),
            week_count=len(s.weeks),
        )
        result.append(r)
    return result


@router.post("/sessions", response_model=SessionRead, status_code=201, dependencies=[Depends(require_admin_api)])
def create_session(data: SessionCreate, db: Session = Depends(get_db)):
    session = SessionModel(**data.model_dump())
    db.add(session)
    db.commit()
    db.refresh(session)
    return SessionRead(
        id=session.id,
        name=session.name,
        type=session.type,
        start_date=session.start_date,
        end_date=session.end_date,
        member_count=0,
        week_count=0,
    )


@router.get("/sessions/{session_id}", response_model=SessionRead)
def get_session(session_id: int, db: Session = Depends(get_db)):
    s = db.query(SessionModel).filter(SessionModel.id == session_id).first()
    if not s:
        raise HTTPException(status_code=404, detail="세션을 찾을 수 없습니다.")
    return SessionRead(
        id=s.id,
        name=s.name,
        type=s.type,
        start_date=s.start_date,
        end_date=s.end_date,
        member_count=len(s.members),
        week_count=len(s.weeks),
    )


@router.put("/sessions/{session_id}", response_model=SessionRead, dependencies=[Depends(require_admin_api)])
def update_session(session_id: int, data: SessionUpdate, db: Session = Depends(get_db)):
    s = db.query(SessionModel).filter(SessionModel.id == session_id).first()
    if not s:
        raise HTTPException(status_code=404, detail="세션을 찾을 수 없습니다.")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(s, field, value)
    db.commit()
    db.refresh(s)
    return SessionRead(
        id=s.id,
        name=s.name,
        type=s.type,
        start_date=s.start_date,
        end_date=s.end_date,
        member_count=len(s.members),
        week_count=len(s.weeks),
    )


@router.delete("/sessions/{session_id}", status_code=204, dependencies=[Depends(require_admin_api)])
def delete_session(session_id: int, db: Session = Depends(get_db)):
    s = db.query(SessionModel).filter(SessionModel.id == session_id).first()
    if not s:
        raise HTTPException(status_code=404, detail="세션을 찾을 수 없습니다.")
    db.delete(s)
    db.commit()
