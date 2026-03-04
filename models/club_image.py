from datetime import datetime
from sqlalchemy import Integer, String, LargeBinary, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from database import Base


class ClubImage(Base):
    __tablename__ = "club_images"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str] = mapped_column(String(100), nullable=False, default="image/jpeg")
    data: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    caption: Mapped[str] = mapped_column(String(500), nullable=False, default="")
