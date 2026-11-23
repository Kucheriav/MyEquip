import pytest
from app.crud.item_parameter_value_crud import item_parameter_value_crud
from app.schemas.item_parameter_value_schema import ItemParameterValueCreate


@pytest.mark.asyncio
async def test_create_item_parameter_value(db_session):
    data = ItemParameterValueCreate(item_id=1, parameter_id=1)
    result = await item_parameter_value_crud.create(db_session, obj_in=data)
    assert result.item_id == 1
    assert result.parameter_id == 1


@pytest.mark.asyncio
async def test_get_by_item(db_session):
    data = ItemParameterValueCreate(item_id=1, parameter_id=1)
    await item_parameter_value_crud.create(db_session, obj_in=data)
    
    result = await item_parameter_value_crud.get_by_item(db_session, 1)
    assert len(result) == 1


@pytest.mark.asyncio
async def test_get_by_parameter(db_session):
    data = ItemParameterValueCreate(item_id=1, parameter_id=1)
    await item_parameter_value_crud.create(db_session, obj_in=data)
    
    result = await item_parameter_value_crud.get_by_parameter(db_session, 1)
    assert len(result) == 1


@pytest.mark.asyncio
async def test_delete_item_parameter_value(db_session):
    data = ItemParameterValueCreate(item_id=1, parameter_id=1)
    created = await item_parameter_value_crud.create(db_session, obj_in=data)
    item_id = created.id
    
    result = await item_parameter_value_crud.delete(db_session, item_id)
    assert result is True