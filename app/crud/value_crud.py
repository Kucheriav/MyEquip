from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models import Value
from app.schemas.value_schema import ValueCreate, ValueUpdate
from app.crud.base_crud import BaseCRUD
from typing import List


class ValueCRUD(BaseCRUD[Value, ValueCreate, ValueUpdate]):
    def __init__(self):
        super().__init__(Value)

    async def get_by_parameter(self, db: AsyncSession, parameter_id: int) -> List[Value]:
        result = await db.execute(select(Value).filter(Value.parameter_id == parameter_id))
        return list(result.scalars().all())


value_crud = ValueCRUD()