import pytest
from app.crud.user_crud import user_crud
from app.schemas.user_schema import UserCreate


@pytest.mark.asyncio
async def test_create_user(db_session):
    user_data = UserCreate(
        name="John",
        surname="Doe",
        email="john@example.com",
        phone="+1234567890",
        pswd_hash="hashed_password"
    )
    result = await user_crud.create(db_session, obj_in=user_data)
    
    assert result.name == "John"
    assert result.surname == "Doe"
    assert result.email == "john@example.com"
    assert result.id is not None


@pytest.mark.asyncio
async def test_get_by_email(db_session):
    user_data = UserCreate(
        name="John",
        surname="Doe",
        email="john@example.com",
        phone="+1234567890",
        pswd_hash="hashed_password"
    )
    await user_crud.create(db_session, obj_in=user_data)
    
    result = await user_crud.get_by_email(db_session, "john@example.com")
    
    assert result is not None
    assert result.email == "john@example.com"


@pytest.mark.asyncio
async def test_get_by_email_not_found(db_session):
    result = await user_crud.get_by_email(db_session, "notfound@example.com")
    
    assert result is None


@pytest.mark.asyncio
async def test_get_by_phone(db_session):
    user_data = UserCreate(
        name="John",
        surname="Doe",
        email="john@example.com",
        phone="+1234567890",
        pswd_hash="hashed_password"
    )
    await user_crud.create(db_session, obj_in=user_data)
    
    result = await user_crud.get_by_phone(db_session, "+1234567890")
    
    assert result is not None
    assert result.phone == "+1234567890"