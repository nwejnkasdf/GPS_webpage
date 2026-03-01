import enum
from datetime import date
from sqlalchemy import ForeignKey, Date, Integer, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from database import Base


class CriteriaMode(str, enum.Enum):
    AND = "AND"
    OR = "OR"


class Week(Base):
    __tablename__ = "weeks"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("sessions.id"), nullable=False)
    week_number: Mapped[int] = mapped_column(Integer, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    min_gold_problems: Mapped[int] = mapped_column(Integer, default=0)
    min_total_problems: Mapped[int] = mapped_column(Integer, default=1)
    criteria_mode: Mapped[CriteriaMode] = mapped_column(
        Enum(CriteriaMode), default=CriteriaMode.AND
    )

    session: Mapped["Session"] = relationship(back_populates="weeks")  # noqa: F821
    problems: Mapped[list["WeekProblem"]] = relationship(  # noqa: F821
        back_populates="week", cascade="all, delete-orphan"
    )
    attendances: Mapped[list["Attendance"]] = relationship(  # noqa: F821
        back_populates="week", cascade="all, delete-orphan"
    )
