from pydantic import BaseModel
from datetime import date
from typing import Optional


class DistributionBase(BaseModel):
    item_id: int
    giver_id: int
    getter_id: int
    date: date
    expiration_date: Optional[date] = None
    status: str = 'issued'
    comment: Optional[str] = None


class DistributionCreate(DistributionBase):
    pass


class DistributionUpdate(BaseModel):
    expiration_date: Optional[date] = None
    status: Optional[str] = None
    accepter_id: Optional[int] = None
    accepting_date: Optional[date] = None
    comment: Optional[str] = None


class DistributionResponse(DistributionBase):
    id: int
    accepter_id: Optional[int] = None
    accepting_date: Optional[date] = None

    class Config:
        from_attributes = True