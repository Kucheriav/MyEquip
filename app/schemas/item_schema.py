from pydantic import BaseModel
from typing import Optional


class ItemBase(BaseModel):
    name: str
    category_id: int
    storage_id: int
    owner_id: int
    status: str = 'available'
    serial_number: Optional[str] = None


class ItemCreate(ItemBase):
    pass


class ItemUpdate(BaseModel):
    name: Optional[str] = None
    category_id: Optional[int] = None
    storage_id: Optional[int] = None
    status: Optional[str] = None
    serial_number: Optional[str] = None


class ItemResponse(ItemBase):
    id: int

    class Config:
        from_attributes = True