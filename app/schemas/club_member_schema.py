from pydantic import BaseModel
from typing import Optional

from app.schemas.user_schema import UserResponse


class ClubMemberCreate(BaseModel):
    user_id: int
    role: str = 'tourist'  # 'storekeeper' or 'tourist' (leader is not assignable)


class ClubMemberResponse(BaseModel):
    id: int
    user_id: int
    club_id: int
    role: str
    user: Optional[UserResponse] = None

    class Config:
        from_attributes = True
