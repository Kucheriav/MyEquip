from pydantic import BaseModel, EmailStr
from datetime import date
from typing import List, Optional


class UserBase(BaseModel):
    name: str
    surname: str
    last_name: Optional[str] = None
    date_of_birth: Optional[date] = None
    email: Optional[EmailStr] = None  # tourists may have no email
    phone: str
    status: str = 'guest'


class UserCreate(UserBase):
    pswd_hash: Optional[str] = None  # None = tourist without an account
    club_id: Optional[int] = None  # required: the club the tourist belongs to


class UserUpdate(BaseModel):
    name: Optional[str] = None
    surname: Optional[str] = None
    last_name: Optional[str] = None
    date_of_birth: Optional[date] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    status: Optional[str] = None


class UserClubRole(BaseModel):
    club_id: int
    role: str  # leader / storekeeper / tourist - role inside that club


class UserResponse(UserBase):
    id: int
    role: str = 'tourist'
    club_ids: List[int] = []
    # Per-club roles: the GUI needs them to offer only club staff as
    # givers/accepters (a user may be a tourist here and a storekeeper there).
    memberships: List[UserClubRole] = []

    class Config:
        from_attributes = True
