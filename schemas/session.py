from datetime import date
from pydantic import BaseModel
from models.session import SessionType


class SessionCreate(BaseModel):
    name: str
    type: SessionType
    start_date: date
    end_date: date


class SessionUpdate(BaseModel):
    name: str | None = None
    type: SessionType | None = None
    start_date: date | None = None
    end_date: date | None = None


class SessionRead(BaseModel):
    id: int
    name: str
    type: SessionType
    start_date: date
    end_date: date
    member_count: int = 0
    week_count: int = 0

    model_config = {"from_attributes": True}
