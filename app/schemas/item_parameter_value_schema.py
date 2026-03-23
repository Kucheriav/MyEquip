from pydantic import BaseModel
from typing import Optional


class ItemParameterValueBase(BaseModel):
    item_id: int
    parameter_id: int
    value_id: Optional[int] = None
    custom_value: Optional[str] = None


class ItemParameterValueCreate(ItemParameterValueBase):
    pass


class ItemParameterValueResponse(ItemParameterValueBase):
    id: int

    class Config:
        from_attributes = True