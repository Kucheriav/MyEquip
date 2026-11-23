from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models import Parameter
from app.schemas.parameter_schema import ParameterCreate, ParameterUpdate
from app.crud.base_crud import BaseCRUD


class ParameterCRUD(BaseCRUD[Parameter, ParameterCreate, ParameterUpdate]):
    def __init__(self):
        super().__init__(Parameter)

    async def get_by_name(self, db: AsyncSession, name: str) -> Parameter:
        result = await db.execute(select(Parameter).filter(Parameter.name == name))
        return result.scalar_one_or_none()


parameter_crud = ParameterCRUD()