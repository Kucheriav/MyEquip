import pytest
from app.crud.parameter_crud import parameter_crud
from app.schemas.parameter_schema import ParameterCreate


@pytest.mark.asyncio
async def test_create_parameter(db_session):
    data = ParameterCreate(name="size", param_type="str")
    result = await parameter_crud.create(db_session, obj_in=data)
    assert result.name == "size"
    assert result.param_type == "str"


@pytest.mark.asyncio
async def test_get_by_name(db_session):
    data = ParameterCreate(name="weight", param_type="float")
    await parameter_crud.create(db_session, obj_in=data)
    
    result = await parameter_crud.get_by_name(db_session, "weight")
    assert result is not None
    assert result.param_type == "float"


@pytest.mark.asyncio
async def test_get_by_name_not_found(db_session):
    result = await parameter_crud.get_by_name(db_session, "nonexistent")
    assert result is None