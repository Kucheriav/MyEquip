from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models import Category
from app.schemas.category_schema import CategoryCreate, CategoryUpdate
from app.crud.base_crud import BaseCRUD
from typing import List


class CategoryCRUD(BaseCRUD[Category, CategoryCreate, CategoryUpdate]):
    def __init__(self):
        super().__init__(Category)

    async def get_by_club(self, db: AsyncSession, club_id: int) -> List[Category]:
        result = await db.execute(select(Category).filter(Category.club_id == club_id))
        return list(result.scalars().all())

    async def get_root_categories(self, db: AsyncSession, club_id: int) -> List[Category]:
        result = await db.execute(
            select(Category).filter(
                Category.club_id == club_id,
                Category.parent_id == None
            ))
        return list(result.scalars().all())


category_crud = CategoryCRUD()