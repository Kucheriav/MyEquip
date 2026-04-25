import pytest
from app.crud.club_crud import club_crud
from app.schemas.club_schema import ClubCreate


@pytest.mark.asyncio
async def test_create_club(db_session):
    club_data = ClubCreate(name="Test Club")
    result = await club_crud.create(db_session, obj_in=club_data)
    
    assert result.name == "Test Club"
    assert result.id is not None


@pytest.mark.asyncio
async def test_get_by_name(db_session):
    club_data = ClubCreate(name="My Club")
    await club_crud.create(db_session, obj_in=club_data)
    
    result = await club_crud.get_by_name(db_session, "My Club")
    
    assert result is not None
    assert result.name == "My Club"


@pytest.mark.asyncio
async def test_get_by_name_not_found(db_session):
    result = await club_crud.get_by_name(db_session, "Non-existent Club")
    
    assert result is None