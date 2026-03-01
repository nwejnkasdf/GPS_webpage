from sqlalchemy import String, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from database import Base


class Member(Base):
    __tablename__ = "members"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("sessions.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    baekjoon_handle: Mapped[str] = mapped_column(String(100), nullable=False)

    session: Mapped["Session"] = relationship(back_populates="members")  # noqa: F821
    attendances: Mapped[list["Attendance"]] = relationship(  # noqa: F821
        back_populates="member", cascade="all, delete-orphan"
    )
