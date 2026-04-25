import logging

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from fastapi import Depends
from typing import AsyncGenerator
from app.config import config


logger = logging.getLogger("app.database")
DATABASE_URL = config.get_db_url()
logger.info(f"Initializing database engine with URL: {DATABASE_URL}")
engine = create_async_engine(DATABASE_URL)
AsyncSessionMaker = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
Base = declarative_base()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionMaker() as session:
        yield session