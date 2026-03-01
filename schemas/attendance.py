from datetime import datetime
from pydantic import BaseModel


class AttendanceRead(BaseModel):
    id: int
    member_id: int
    week_id: int
    is_present: bool
    solved_gold_count: int
    solved_total_count: int
    last_checked: datetime | None

    model_config = {"from_attributes": True}


class AttendanceCell(BaseModel):
    is_present: bool
    solved_gold_count: int
    solved_total_count: int
    last_checked: datetime | None


class AttendanceRow(BaseModel):
    member_id: int
    member_name: str
    baekjoon_handle: str
    weeks: dict[int, AttendanceCell | None]  # week_id -> cell


class AttendanceTable(BaseModel):
    session_id: int
    weeks: list[dict]  # [{id, week_number, end_date, criteria}]
    rows: list[AttendanceRow]


class CheckTaskStatus(BaseModel):
    task_id: str
    status: str  # queued | running | done | error
    progress: int
    total: int
    errors: list[str]
