from pydantic import BaseModel, EmailStr
from datetime import date
from typing import List, Optional


class UserBase(BaseModel):
    name: str
    surname: str
    last_name: Optional[str] = None
    date_of_birth: Optional[date] = None
    email: EmailStr
    phone: str
    status: str = 'guest'


class UserCreate(UserBase):
    pswd_hash: str


class UserUpdate(BaseModel):
    name: Optional[str] = None
    surname: Optional[str] = None
    last_name: Optional[str] = None
    date_of_birth: Optional[date] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    status: Optional[str] = None


class UserResponse(UserBase):
    id: int

    class Config:
        from_attributes = True