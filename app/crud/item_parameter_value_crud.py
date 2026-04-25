from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models import ItemParameterValue
from app.schemas.item_parameter_value_schema import (
    ItemParameterValueCreate, ItemParameterValueResponse
)
from app.crud.base_crud import BaseCRUD
from typing import List


class ItemParameterValueCRUD(BaseCRUD[ItemParameterValue, ItemParameterValueCreate, ItemParameterValueResponse]):
    def __init__(self):
        super().__init__(ItemParameterValue)

    async def get_by_item(self, db: AsyncSession, item_id: int) -> List[ItemParameterValue]:
        result = await db.execute(
            select(ItemParameterValue).filter(ItemParameterValue.item_id == item_id))
        return list(result.scalars().all())

    async def get_by_parameter(self, db: AsyncSession, parameter_id: int) -> List[ItemParameterValue]:
        result = await db.execute(
            select(ItemParameterValue).filter(ItemParameterValue.parameter_id == parameter_id))
        return list(result.scalars().all())


item_parameter_value_crud = ItemParameterValueCRUD()