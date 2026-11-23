from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models import Storage
from app.schemas.storage_schema import StorageCreate, StorageUpdate
from app.crud.base_crud import BaseCRUD
from typing import List


class StorageCRUD(BaseCRUD[Storage, StorageCreate, StorageUpdate]):
    def __init__(self):
        super().__init__(Storage)

    async def get_by_club(self, db: AsyncSession, club_id: int) -> List[Storage]:
        result = await db.execute(select(Storage).filter(Storage.club_id == club_id))
        return list(result.scalars().all())


storage_crud = StorageCRUD()