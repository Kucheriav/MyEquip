import logging

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base
from fastapi import Depends
from typing import AsyncGenerator
from app.config import config


logger = logging.getLogger("app.database")
Base = declarative_base()


def get_database_url():
    return config.get_db_url()


class Database:
    def __init__(self):
        self._engine = None
        self._session_maker = None
    
    @property
    def engine(self):
        if self._engine is None:
            DATABASE_URL = get_database_url()
            logger.info(f"Initializing database engine with URL: {DATABASE_URL}")
            self._engine = create_async_engine(DATABASE_URL)
        return self._engine
    
    @property
    def async_session_maker(self):
        if self._session_maker is None:
            self._session_maker = async_sessionmaker(
                self.engine, 
                class_=AsyncSession, 
                expire_on_commit=False
            )
        return self._session_maker
    
    async def create_session(self) -> AsyncSession:
        return self.async_session_maker()


db_instance = Database()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with db_instance.async_session_maker() as session:
        yield session