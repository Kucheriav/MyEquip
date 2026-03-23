from pydantic import BaseModel
from typing import Optional


class ValueBase(BaseModel):
    value: str
    parameter_id: int


class ValueCreate(ValueBase):
    pass


class ValueUpdate(BaseModel):
    value: Optional[str] = None


class ValueResponse(ValueBase):
    id: int

    class Config:
        from_attributes = True