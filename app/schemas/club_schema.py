from pydantic import BaseModel
from typing import Optional


class ClubBase(BaseModel):
    name: str


class ClubCreate(ClubBase):
    pass


class ClubUpdate(BaseModel):
    name: Optional[str] = None


class ClubResponse(ClubBase):
    id: int

    class Config:
        from_attributes = True