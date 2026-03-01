import csv
import io

from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session as DBSession

from models.attendance import Attendance
from models.member import Member
from models.session import Session as SessionModel
from models.week import Week


def export_session_csv(session_id: int, db: DBSession) -> StreamingResponse:
    s = db.query(SessionModel).filter(SessionModel.id == session_id).first()
    if not s:
        raise ValueError("세션을 찾을 수 없습니다.")

    weeks = (
        db.query(Week)
        .filter(Week.session_id == session_id)
        .order_by(Week.week_number)
        .all()
    )
    members = db.query(Member).filter(Member.session_id == session_id).all()

    member_ids = [m.id for m in members]
    week_ids = [w.id for w in weeks]
    attendances = (
        db.query(Attendance)
        .filter(Attendance.member_id.in_(member_ids), Attendance.week_id.in_(week_ids))
        .all()
    )
    att_map = {(a.member_id, a.week_id): a for a in attendances}

    output = io.StringIO()
    writer = csv.writer(output)

    # Header
    header = ["이름", "BOJ ID"]
    for week in weeks:
        header.append(f"Week{week.week_number}({week.end_date})")
    header.append("총출석")
    writer.writerow(header)

    # Data rows
    for member in members:
        row = [member.name, member.baekjoon_handle]
        total_present = 0
        for week in weeks:
            att = att_map.get((member.id, week.id))
            if att is None:
                row.append("-")
            elif att.is_present:
                row.append("O")
                total_present += 1
            else:
                row.append("X")
        row.append(total_present)
        writer.writerow(row)

    output.seek(0)
    filename = f"attendance_{s.name.replace(' ', '_')}.csv"
    return StreamingResponse(
        iter([output.getvalue().encode("utf-8-sig")]),  # BOM for Excel Korean
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{filename}"},
    )
