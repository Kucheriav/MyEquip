from pydantic import BaseModel
from typing import Dict, Any

class ItemCreate(BaseModel):
    name: str
    template: str
    properties: Dict[str, Any]