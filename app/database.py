import logging

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.config import config


logger = logging.getLogger("app.database")
DATABASE_URL =  config.get_db_url()
logger.info(f"Initializing database engine with URL: {DATABASE_URL}")
engine = create_async_engine(DATABASE_URL, connect_args={"check_same_thread": False})
AsyncSessionMaker = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
Base = declarative_base()


def connection(method):
    async def wrapper(*args, **kwargs):
        logger.info(f"Opening a new database session for method: {method.__name__}")
        async with AsyncSessionMaker() as session:
            try:
                result = await method(*args, session=session, **kwargs)
                logger.info(f"Method {method.__name__} completed successfully")
                return result
            finally:
                logger.info(f"Database session for method {method.__name__} closed")

    return wrapper