import pytest
from app.crud.storage_crud import storage_crud
from app.schemas.storage_schema import StorageCreate


@pytest.mark.asyncio
async def test_create_storage(db_session):
    data = StorageCreate(name="Main Storage", club_id=1, address="Address 1")
    result = await storage_crud.create(db_session, obj_in=data)
    assert result.name == "Main Storage"
    assert result.club_id == 1


@pytest.mark.asyncio
async def test_get_by_club(db_session):
    data = StorageCreate(name="Storage 1", club_id=1)
    await storage_crud.create(db_session, obj_in=data)
    
    result = await storage_crud.get_by_club(db_session, 1)
    assert len(result) == 1


@pytest.mark.asyncio
async def test_get_by_club_empty(db_session):
    result = await storage_crud.get_by_club(db_session, 999)
    assert len(result) == 0