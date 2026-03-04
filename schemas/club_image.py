from datetime import datetime
from pydantic import BaseModel


class ClubImageRead(BaseModel):
    id: int
    filename: str
    content_type: str
    uploaded_at: datetime
    sort_order: int
    caption: str

    model_config = {"from_attributes": True}


class ClubImageUpdate(BaseModel):
    sort_order: int | None = None
    caption: str | None = None
