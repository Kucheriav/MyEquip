from pydantic import BaseModel, ConfigDict
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
    model_config = ConfigDict(from_attributes=True)