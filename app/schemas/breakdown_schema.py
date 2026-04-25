from pydantic import BaseModel
from datetime import date
from typing import Optional


class BreakdownBase(BaseModel):
    item_id: int
    comment: str
    date: date
    repaired_date: Optional[date] = None
    repairer_id: Optional[int] = None
    status: str = 'reported'


class BreakdownCreate(BreakdownBase):
    pass


class BreakdownUpdate(BaseModel):
    comment: Optional[str] = None
    repaired_date: Optional[date] = None
    repairer_id: Optional[int] = None
    status: Optional[str] = None


class BreakdownResponse(BreakdownBase):
    id: int

    class Config:
        from_attributes = True