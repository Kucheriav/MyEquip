from pydantic import BaseModel, ConfigDict
from typing import Optional, List


class CategoryBase(BaseModel):
    title: str
    club_id: int
    parent_id: Optional[int] = None


class CategoryCreate(CategoryBase):
    pass


class CategoryUpdate(BaseModel):
    title: Optional[str] = None
    parent_id: Optional[int] = None


class CategoryResponse(CategoryBase):
    id: int
    model_config = ConfigDict(from_attributes=True)