from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, LargeBinary, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from database import Base


class BojGameProblem(Base):
    __tablename__ = "boj_game_pool_problems"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    problem_number: Mapped[int] = mapped_column(Integer, nullable=False, unique=True)
    title: Mapped[str] = mapped_column(String(200), default="")
    difficulty: Mapped[int] = mapped_column(Integer, nullable=False)
    image_data: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    image_content_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class BojGameRound(Base):
    __tablename__ = "boj_game_rounds"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(100), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=False)
    last_result_status: Mapped[str] = mapped_column(String(20), default="pending")
    last_submitted_order: Mapped[list[int] | None] = mapped_column(JSON, nullable=True)
    last_attempt_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    problems: Mapped[list["BojGameRoundProblem"]] = relationship(  # noqa: F821
        back_populates="round",
        cascade="all, delete-orphan",
    )


class BojGameRoundProblem(Base):
    __tablename__ = "boj_game_round_problems"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    round_id: Mapped[int] = mapped_column(ForeignKey("boj_game_rounds.id"), nullable=False)
    problem_number: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String(200), default="")
    difficulty: Mapped[int] = mapped_column(Integer, nullable=False)
    image_data: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    image_content_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    display_order: Mapped[int] = mapped_column(Integer, default=0)

    round: Mapped["BojGameRound"] = relationship(back_populates="problems")  # noqa: F821
