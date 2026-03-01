from datetime import datetime
from sqlalchemy import ForeignKey, Boolean, Integer, DateTime, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from database import Base


class Attendance(Base):
    __tablename__ = "attendances"
    __table_args__ = (UniqueConstraint("member_id", "week_id", name="uq_member_week"),)

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    member_id: Mapped[int] = mapped_column(ForeignKey("members.id"), nullable=False)
    week_id: Mapped[int] = mapped_column(ForeignKey("weeks.id"), nullable=False)
    is_present: Mapped[bool] = mapped_column(Boolean, default=False)
    solved_gold_count: Mapped[int] = mapped_column(Integer, default=0)
    solved_total_count: Mapped[int] = mapped_column(Integer, default=0)
    last_checked: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    member: Mapped["Member"] = relationship(back_populates="attendances")  # noqa: F821
    week: Mapped["Week"] = relationship(back_populates="attendances")  # noqa: F821
