from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models import Club
from app.schemas.club_schema import ClubCreate, ClubUpdate
from app.crud.base_crud import BaseCRUD


class ClubCRUD(BaseCRUD[Club, ClubCreate, ClubUpdate]):
    def __init__(self):
        super().__init__(Club)

    async def get_by_name(self, db: AsyncSession, name: str) -> Club:
        result = await db.execute(select(Club).filter(Club.name == name))
        return result.scalar_one_or_none()


club_crud = ClubCRUD()