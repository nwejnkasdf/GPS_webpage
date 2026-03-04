from pydantic import BaseModel


class ClubInfoUpdate(BaseModel):
    intro_text: str


class ClubInfoRead(BaseModel):
    id: int
    intro_text: str

    model_config = {"from_attributes": True}
