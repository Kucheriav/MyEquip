from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models import User
from app.schemas.user_schema import UserCreate, UserUpdate
from app.crud.base_crud import BaseCRUD
from typing import List


class UserCRUD(BaseCRUD[User, UserCreate, UserUpdate]):
    def __init__(self):
        super().__init__(User)

    async def get_by_email(self, db: AsyncSession, email: str) -> User:
        result = await db.execute(select(User).filter(User.email == email))
        return result.scalar_one_or_none()

    async def get_by_phone(self, db: AsyncSession, phone: str) -> User:
        result = await db.execute(select(User).filter(User.phone == phone))
        return result.scalar_one_or_none()

    async def get_by_club(self, db: AsyncSession, club_id: int) -> List[User]:
        result = await db.execute(
            select(User).join(User.clubs).filter(User.clubs.any(id=club_id))
        )
        return list(result.scalars().all())


user_crud = UserCRUD()