from pydantic import BaseModel, Field


class TelepathyTeamUpdateItem(BaseModel):
    id: int
    name: str = Field(min_length=1, max_length=50)


class TelepathyTeamsUpdate(BaseModel):
    teams: list[TelepathyTeamUpdateItem]


class TelepathyRoundCreate(BaseModel):
    title: str = Field(min_length=1, max_length=100)
    prompt: str = Field(default="", max_length=500)


class TelepathyRoundUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=100)
    prompt: str | None = Field(default=None, max_length=500)


class TelepathySubmissionCreate(BaseModel):
    team_id: int
    ranking: list[int] = Field(min_length=1)


class BojConfigUpdate(BaseModel):
    sample_size: int = Field(ge=2, le=10)


class BojSubmitRequest(BaseModel):
    ordered_problem_ids: list[int] = Field(min_length=1)
