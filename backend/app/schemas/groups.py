from datetime import datetime

from pydantic import BaseModel, Field


class GroupCreate(BaseModel):
    name: str = Field(min_length=1, max_length=80)

    model_config = {"json_schema_extra": {"examples": [{"name": "Alvin Brothers"}]}}


class GroupJoin(BaseModel):
    invite_code: str = Field(min_length=1, max_length=64)

    model_config = {"json_schema_extra": {"examples": [{"invite_code": "Xk3pQ1z8"}]}}


class GroupRead(BaseModel):
    """A group as seen by one of its members.

    invite_code is included because members need it to invite others; it is only
    ever returned to athletes who already belong to the group.
    """

    id: int
    name: str
    invite_code: str
    created_by: int | None
    created_at: datetime
    member_count: int


class GroupMember(BaseModel):
    athlete_id: int
    name: str
    joined_at: datetime
