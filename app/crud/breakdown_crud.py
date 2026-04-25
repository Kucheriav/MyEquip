from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models import Breakdown
from app.schemas.breakdown_schema import BreakdownCreate, BreakdownUpdate
from app.crud.base_crud import BaseCRUD
from typing import List


class BreakdownCRUD(BaseCRUD[Breakdown, BreakdownCreate, BreakdownUpdate]):
    def __init__(self):
        super().__init__(Breakdown)

    async def get_by_item(self, db: AsyncSession, item_id: int) -> List[Breakdown]:
        result = await db.execute(select(Breakdown).filter(Breakdown.item_id == item_id))
        return list(result.scalars().all())

    async def get_unrepaired(self, db: AsyncSession) -> List[Breakdown]:
        result = await db.execute(select(Breakdown).filter(Breakdown.repaired_date == None))
        return list(result.scalars().all())


breakdown_crud = BreakdownCRUD()