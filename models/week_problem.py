from sqlalchemy import ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from database import Base


class WeekProblem(Base):
    __tablename__ = "week_problems"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    week_id: Mapped[int] = mapped_column(ForeignKey("weeks.id"), nullable=False)
    problem_number: Mapped[int] = mapped_column(Integer, nullable=False)
    # solved.ac level: 0=미확인, 1-5=Bronze, 6-10=Silver, 11-15=Gold,
    # 16-20=Platinum, 21-25=Diamond, 26-30=Ruby
    difficulty: Mapped[int] = mapped_column(Integer, default=0)

    week: Mapped["Week"] = relationship(back_populates="problems")  # noqa: F821
