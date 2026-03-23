from pydantic import BaseModel
from typing import Optional


class StorageBase(BaseModel):
    name: str
    address: Optional[str] = None
    club_id: int


class StorageCreate(StorageBase):
    pass


class StorageUpdate(BaseModel):
    name: Optional[str] = None
    address: Optional[str] = None


class StorageResponse(StorageBase):
    id: int

    class Config:
        from_attributes = True