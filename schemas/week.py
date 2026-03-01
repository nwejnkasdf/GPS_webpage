from datetime import date
from pydantic import BaseModel
from models.week import CriteriaMode


class WeekCreate(BaseModel):
    week_number: int
    end_date: date
    min_gold_problems: int = 0
    min_total_problems: int = 1
    criteria_mode: CriteriaMode = CriteriaMode.AND


class WeekUpdate(BaseModel):
    week_number: int | None = None
    end_date: date | None = None
    min_gold_problems: int | None = None
    min_total_problems: int | None = None
    criteria_mode: CriteriaMode | None = None


class WeekProblemRead(BaseModel):
    id: int
    week_id: int
    problem_number: int
    difficulty: int
    difficulty_label: str = ""
    difficulty_tier: str = "unknown"

    model_config = {"from_attributes": True}


class WeekRead(BaseModel):
    id: int
    session_id: int
    week_number: int
    end_date: date
    min_gold_problems: int
    min_total_problems: int
    criteria_mode: CriteriaMode
    problems: list[WeekProblemRead] = []

    model_config = {"from_attributes": True}
