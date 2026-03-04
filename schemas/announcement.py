from datetime import date, datetime
from pydantic import BaseModel


class AnnouncementCreate(BaseModel):
    title: str
    body: str = ""
    event_date: date | None = None
    is_pinned: bool = False


class AnnouncementUpdate(BaseModel):
    title: str | None = None
    body: str | None = None
    event_date: date | None = None
    is_pinned: bool | None = None


class AnnouncementRead(BaseModel):
    id: int
    title: str
    body: str
    event_date: date | None
    created_at: datetime
    updated_at: datetime
    is_pinned: bool

    model_config = {"from_attributes": True}
