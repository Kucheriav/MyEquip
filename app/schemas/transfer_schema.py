from pydantic import BaseModel
from datetime import date
from typing import Optional


class TransferBase(BaseModel):
    item_id: int
    from_storage_id: int
    to_storage_id: int
    date: date
    mover_id: Optional[int] = None
    receiver_id: Optional[int] = None
    comment: Optional[str] = None


class TransferCreate(TransferBase):
    pass


class TransferResponse(TransferBase):
    id: int

    class Config:
        from_attributes = True
