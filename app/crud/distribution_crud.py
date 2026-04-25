from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models import Distribution
from app.schemas.distribution_schema import DistributionCreate, DistributionUpdate
from app.crud.base_crud import BaseCRUD
from typing import List
from datetime import date


class DistributionCRUD(BaseCRUD[Distribution, DistributionCreate, DistributionUpdate]):
    def __init__(self):
        super().__init__(Distribution)

    async def get_by_item(self, db: AsyncSession, item_id: int) -> List[Distribution]:
        result = await db.execute(select(Distribution).filter(Distribution.item_id == item_id))
        return list(result.scalars().all())

    async def get_by_user_given(self, db: AsyncSession, user_id: int) -> List[Distribution]:
        result = await db.execute(select(Distribution).filter(Distribution.giver_id == user_id))
        return list(result.scalars().all())

    async def get_by_user_received(self, db: AsyncSession, user_id: int) -> List[Distribution]:
        result = await db.execute(select(Distribution).filter(Distribution.getter_id == user_id))
        return list(result.scalars().all())

    async def get_active_distributions(self, db: AsyncSession) -> List[Distribution]:
        result = await db.execute(
            select(Distribution).filter(Distribution.status == 'issued'))
        return list(result.scalars().all())

    async def get_overdue_distributions(self, db: AsyncSession, today: date) -> List[Distribution]:
        result = await db.execute(
            select(Distribution).filter(
                Distribution.status == 'issued',
                Distribution.expiration_date < today
            ))
        return list(result.scalars().all())


distribution_crud = DistributionCRUD()