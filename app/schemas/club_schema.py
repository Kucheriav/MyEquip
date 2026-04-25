from pydantic import BaseModel, ConfigDict
from typing import Optional


class ClubBase(BaseModel):
    name: str


class ClubCreate(ClubBase):
    pass


class ClubUpdate(BaseModel):
    name: Optional[str] = None


class ClubResponse(ClubBase):
    id: int
    model_config = ConfigDict(from_attributes=True)