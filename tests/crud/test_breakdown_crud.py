import pytest
from datetime import date
from app.crud.breakdown_crud import breakdown_crud
from app.schemas.breakdown_schema import BreakdownCreate


@pytest.mark.asyncio
async def test_create_breakdown(db_session):
    data = BreakdownCreate(item_id=1, comment="Broken screen", date=date.today())
    result = await breakdown_crud.create(db_session, obj_in=data)
    assert result.comment == "Broken screen"
    assert result.status == 'reported'


@pytest.mark.asyncio
async def test_get_by_item(db_session):
    data = BreakdownCreate(item_id=1, comment="Test", date=date.today())
    await breakdown_crud.create(db_session, obj_in=data)
    
    result = await breakdown_crud.get_by_item(db_session, 1)
    assert len(result) == 1


@pytest.mark.asyncio
async def test_get_unrepaired(db_session):
    data = BreakdownCreate(item_id=1, comment="Unrepaired", date=date.today())
    await breakdown_crud.create(db_session, obj_in=data)
    
    result = await breakdown_crud.get_unrepaired(db_session)
    assert len(result) == 1