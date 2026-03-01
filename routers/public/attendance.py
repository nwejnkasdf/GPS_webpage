from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from database import get_db
from models.session import Session as SessionModel
from routers.admin.attendance import get_session_attendance
from schemas.attendance import AttendanceTable
from schemas.session import SessionRead
from services.export_service import export_session_csv

router = APIRouter()


@router.get("/public/sessions", response_model=list[SessionRead])
def public_list_sessions(db: Session = Depends(get_db)):
    sessions = db.query(SessionModel).order_by(SessionModel.start_date.desc()).all()
    return [
        SessionRead(
            id=s.id,
            name=s.name,
            type=s.type,
            start_date=s.start_date,
            end_date=s.end_date,
            member_count=len(s.members),
            week_count=len(s.weeks),
        )
        for s in sessions
    ]


@router.get("/public/sessions/{session_id}/attendance", response_model=AttendanceTable)
def public_get_attendance(session_id: int, db: Session = Depends(get_db)):
    # Reuse admin endpoint logic
    return get_session_attendance(session_id, db)


@router.get("/public/sessions/{session_id}/attendance/export")
def public_export_csv(session_id: int, db: Session = Depends(get_db)) -> StreamingResponse:
    try:
        return export_session_csv(session_id, db)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
