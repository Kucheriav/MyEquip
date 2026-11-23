from pydantic import BaseModel, ConfigDict
from typing import Optional


class ParameterBase(BaseModel):
    name: str
    param_type: str  # 'int', 'bool', 'str', 'float'


class ParameterCreate(ParameterBase):
    pass


class ParameterUpdate(BaseModel):
    name: Optional[str] = None
    param_type: Optional[str] = None


class ParameterResponse(ParameterBase):
    id: int
    model_config = ConfigDict(from_attributes=True)