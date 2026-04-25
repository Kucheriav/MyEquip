from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models import Item
from app.schemas.item_schema import ItemCreate, ItemUpdate
from app.crud.base_crud import BaseCRUD
from typing import List


class ItemCRUD(BaseCRUD[Item, ItemCreate, ItemUpdate]):
    def __init__(self):
        super().__init__(Item)

    async def get_by_storage(self, db: AsyncSession, storage_id: int) -> List[Item]:
        result = await db.execute(select(Item).filter(Item.storage_id == storage_id))
        return list(result.scalars().all())

    async def get_by_owner(self, db: AsyncSession, owner_id: int) -> List[Item]:
        result = await db.execute(select(Item).filter(Item.owner_id == owner_id))
        return list(result.scalars().all())

    async def get_by_category(self, db: AsyncSession, category_id: int) -> List[Item]:
        result = await db.execute(select(Item).filter(Item.category_id == category_id))
        return list(result.scalars().all())

    async def get_by_status(self, db: AsyncSession, status: str) -> List[Item]:
        result = await db.execute(select(Item).filter(Item.status == status))
        return list(result.scalars().all())

    async def get_by_serial_number(self, db: AsyncSession, serial_number: str) -> Item:
        result = await db.execute(select(Item).filter(Item.serial_number == serial_number))
        return result.scalar_one_or_none()


item_crud = ItemCRUD()