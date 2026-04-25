import pytest
from app.crud.value_crud import value_crud
from app.schemas.value_schema import ValueCreate


@pytest.mark.asyncio
async def test_create_value(db_session):
    data = ValueCreate(value="S", parameter_id=1)
    result = await value_crud.create(db_session, obj_in=data)
    assert result.value == "S"
    assert result.parameter_id == 1


@pytest.mark.asyncio
async def test_get_by_parameter(db_session):
    data = ValueCreate(value="M", parameter_id=1)
    await value_crud.create(db_session, obj_in=data)
    
    result = await value_crud.get_by_parameter(db_session, 1)
    assert len(result) == 1