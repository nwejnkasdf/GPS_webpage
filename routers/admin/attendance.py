import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.orm import Session

from auth import require_admin_api
from database import get_db
from models.attendance import Attendance
from models.member import Member
from models.session import Session as SessionModel
from models.week import Week
from fastapi.responses import StreamingResponse

from schemas.attendance import AttendanceCell, AttendanceRow, AttendanceTable, CheckTaskStatus
from services.attendance_service import check_session_attendance, check_week_attendance
from services.export_service import export_session_csv

router = APIRouter()

# In-memory task store (single-process deployment)
check_tasks: dict[str, dict] = {}


@router.post("/sessions/{session_id}/check", dependencies=[Depends(require_admin_api)])
async def trigger_session_check(
    session_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    s = db.query(SessionModel).filter(SessionModel.id == session_id).first()
    if not s:
        raise HTTPException(status_code=404, detail="세션을 찾을 수 없습니다.")

    task_id = str(uuid.uuid4())
    check_tasks[task_id] = {"status": "queued", "progress": 0, "total": 0, "errors": []}
    background_tasks.add_task(check_session_attendance, db, session_id, check_tasks, task_id)
    return {"task_id": task_id, "status": "queued"}


@router.post("/weeks/{week_id}/check", dependencies=[Depends(require_admin_api)])
async def trigger_week_check(
    week_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    w = db.query(Week).filter(Week.id == week_id).first()
    if not w:
        raise HTTPException(status_code=404, detail="주차를 찾을 수 없습니다.")

    task_id = str(uuid.uuid4())
    check_tasks[task_id] = {"status": "queued", "progress": 0, "total": 0, "errors": []}
    background_tasks.add_task(check_week_attendance, db, week_id, check_tasks, task_id)
    return {"task_id": task_id, "status": "queued"}


@router.get("/check/status", response_model=CheckTaskStatus)
def get_check_status(task_id: str):
    task = check_tasks.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="태스크를 찾을 수 없습니다.")
    return CheckTaskStatus(task_id=task_id, **task)


@router.get("/sessions/{session_id}/attendance", response_model=AttendanceTable)
def get_session_attendance(session_id: int, db: Session = Depends(get_db)):
    s = db.query(SessionModel).filter(SessionModel.id == session_id).first()
    if not s:
        raise HTTPException(status_code=404, detail="세션을 찾을 수 없습니다.")

    weeks = (
        db.query(Week)
        .filter(Week.session_id == session_id)
        .order_by(Week.week_number)
        .all()
    )
    members = db.query(Member).filter(Member.session_id == session_id).all()

    # Build attendance map: (member_id, week_id) -> Attendance
    member_ids = [m.id for m in members]
    week_ids = [w.id for w in weeks]
    attendances = (
        db.query(Attendance)
        .filter(Attendance.member_id.in_(member_ids), Attendance.week_id.in_(week_ids))
        .all()
    )
    att_map = {(a.member_id, a.week_id): a for a in attendances}

    weeks_info = [
        {
            "id": w.id,
            "week_number": w.week_number,
            "end_date": w.end_date.isoformat(),
            "min_gold_problems": w.min_gold_problems,
            "min_total_problems": w.min_total_problems,
            "criteria_mode": w.criteria_mode.value,
            "problem_count": len(w.problems),
        }
        for w in weeks
    ]

    rows = []
    for member in members:
        week_cells: dict[int, AttendanceCell | None] = {}
        for week in weeks:
            att = att_map.get((member.id, week.id))
            if att:
                week_cells[week.id] = AttendanceCell(
                    is_present=att.is_present,
                    solved_gold_count=att.solved_gold_count,
                    solved_total_count=att.solved_total_count,
                    last_checked=att.last_checked,
                )
            else:
                week_cells[week.id] = None
        rows.append(
            AttendanceRow(
                member_id=member.id,
                member_name=member.name,
                baekjoon_handle=member.baekjoon_handle,
                weeks=week_cells,
            )
        )

    return AttendanceTable(session_id=session_id, weeks=weeks_info, rows=rows)


@router.get("/sessions/{session_id}/attendance/export")
def export_attendance_csv(session_id: int, db: Session = Depends(get_db)) -> StreamingResponse:
    try:
        return export_session_csv(session_id, db)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
