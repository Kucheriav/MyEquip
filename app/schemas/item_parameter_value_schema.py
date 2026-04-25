from pydantic import BaseModel, ConfigDict
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
    model_config = ConfigDict(from_attributes=True)