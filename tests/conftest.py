import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker


TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture
async def setup_db():
    from app.database import Base
    from app.models.user_model import User
    from app.models.club_model import Club
    from app.models.category_model import Category
    from app.models.parameter_model import Parameter
    from app.models.value_model import Value
    from app.models.item_model import Item
    from app.models.storage_model import Storage
    from app.models.distribution_model import Distribution
    from app.models.breakdown_model import Breakdown
    from app.models.item_parameter_value_model import ItemParameterValue
    
    test_engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield test_engine
    
    await test_engine.dispose()


@pytest_asyncio.fixture
async def db_session(setup_db):
    async_session = async_sessionmaker(setup_db, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        yield session
        await session.rollback()