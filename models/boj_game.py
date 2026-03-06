from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, LargeBinary, String
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


class BojGameConfig(Base):
    __tablename__ = "boj_game_configs"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    sample_size: Mapped[int] = mapped_column(Integer, default=4)
    current_set_nonce: Mapped[int] = mapped_column(Integer, default=0)
    last_result_status: Mapped[str] = mapped_column(String(20), default="pending")
    last_submitted_order: Mapped[list[int] | None] = mapped_column(JSON, nullable=True)
    last_attempt_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    current_problems: Mapped[list["BojGameCurrentProblem"]] = relationship(  # noqa: F821
        back_populates="config",
        cascade="all, delete-orphan",
        order_by="BojGameCurrentProblem.display_order",
    )


class BojGameCurrentProblem(Base):
    __tablename__ = "boj_game_current_problems"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    config_id: Mapped[int] = mapped_column(ForeignKey("boj_game_configs.id"), nullable=False)
    pool_problem_id: Mapped[int] = mapped_column(ForeignKey("boj_game_pool_problems.id"), nullable=False)
    display_order: Mapped[int] = mapped_column(Integer, default=0)

    config: Mapped["BojGameConfig"] = relationship(back_populates="current_problems")  # noqa: F821
    pool_problem: Mapped["BojGameProblem"] = relationship()  # noqa: F821
