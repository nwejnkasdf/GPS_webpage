from pydantic import BaseModel


class MemberCreate(BaseModel):
    name: str
    baekjoon_handle: str


class MemberUpdate(BaseModel):
    name: str | None = None
    baekjoon_handle: str | None = None


class MemberRead(BaseModel):
    id: int
    session_id: int
    name: str
    baekjoon_handle: str

    model_config = {"from_attributes": True}


class MemberBulkItem(BaseModel):
    name: str
    baekjoon_handle: str
