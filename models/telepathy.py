import enum
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, LargeBinary, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from database import Base


class TelepathySubmissionRole(str, enum.Enum):
    REPRESENTATIVE = "representative"
    TEAM = "team"


class TelepathyTeam(Base):
    __tablename__ = "telepathy_teams"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    display_order: Mapped[int] = mapped_column(Integer, default=0)

    submissions: Mapped[list["TelepathySubmission"]] = relationship(  # noqa: F821
        back_populates="team",
        cascade="all, delete-orphan",
    )


class TelepathyRound(Base):
    __tablename__ = "telepathy_rounds"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(100), nullable=False)
    prompt: Mapped[str] = mapped_column(Text, default="")
    is_active: Mapped[bool] = mapped_column(Boolean, default=False)
    is_revealed: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    options: Mapped[list["TelepathyOption"]] = relationship(  # noqa: F821
        back_populates="round",
        cascade="all, delete-orphan",
    )
    submissions: Mapped[list["TelepathySubmission"]] = relationship(  # noqa: F821
        back_populates="round",
        cascade="all, delete-orphan",
    )


class TelepathyOption(Base):
    __tablename__ = "telepathy_options"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    round_id: Mapped[int] = mapped_column(ForeignKey("telepathy_rounds.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    image_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    image_data: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    image_content_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    display_order: Mapped[int] = mapped_column(Integer, default=0)

    round: Mapped["TelepathyRound"] = relationship(back_populates="options")  # noqa: F821


class TelepathySubmission(Base):
    __tablename__ = "telepathy_submissions"
    __table_args__ = (
        UniqueConstraint("round_id", "team_id", "role", name="uq_telepathy_submission"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    round_id: Mapped[int] = mapped_column(ForeignKey("telepathy_rounds.id"), nullable=False)
    team_id: Mapped[int] = mapped_column(ForeignKey("telepathy_teams.id"), nullable=False)
    role: Mapped[TelepathySubmissionRole] = mapped_column(nullable=False)
    ranking: Mapped[list[int]] = mapped_column(JSON, default=list)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    round: Mapped["TelepathyRound"] = relationship(back_populates="submissions")  # noqa: F821
    team: Mapped["TelepathyTeam"] = relationship(back_populates="submissions")  # noqa: F821
