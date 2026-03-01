import enum
from datetime import date
from sqlalchemy import String, Enum, Date
from sqlalchemy.orm import Mapped, mapped_column, relationship
from database import Base


class SessionType(str, enum.Enum):
    WINTER = "겨울방학"
    SPRING = "1학기"
    SUMMER = "여름방학"
    FALL = "2학기"


class Session(Base):
    __tablename__ = "sessions"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    type: Mapped[SessionType] = mapped_column(Enum(SessionType), nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)

    members: Mapped[list["Member"]] = relationship(  # noqa: F821
        back_populates="session", cascade="all, delete-orphan"
    )
    weeks: Mapped[list["Week"]] = relationship(  # noqa: F821
        back_populates="session", cascade="all, delete-orphan", order_by="Week.week_number"
    )
