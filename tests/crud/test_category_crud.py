import pytest
from app.crud.category_crud import category_crud
from app.schemas.category_schema import CategoryCreate


@pytest.mark.asyncio
async def test_create_category(db_session):
    data = CategoryCreate(title="Electronics", club_id=1)
    result = await category_crud.create(db_session, obj_in=data)
    assert result.title == "Electronics"
    assert result.club_id == 1


@pytest.mark.asyncio
async def test_get_by_club(db_session):
    data = CategoryCreate(title="Cat 1", club_id=1)
    await category_crud.create(db_session, obj_in=data)
    
    result = await category_crud.get_by_club(db_session, 1)
    assert len(result) == 1


@pytest.mark.asyncio
async def test_get_root_categories(db_session):
    data = CategoryCreate(title="Root Category", club_id=1, parent_id=None)
    await category_crud.create(db_session, obj_in=data)
    
    result = await category_crud.get_root_categories(db_session, 1)
    assert len(result) == 1


@pytest.mark.asyncio
async def test_update_category(db_session):
    data = CategoryCreate(title="Original", club_id=1)
    created = await category_crud.create(db_session, obj_in=data)
    
    from app.schemas.category_schema import CategoryUpdate
    updated = await category_crud.update(db_session, db_obj=created, obj_in=CategoryUpdate(title="Updated"))
    
    assert updated.title == "Updated"


@pytest.mark.asyncio
async def test_delete_category(db_session):
    data = CategoryCreate(title="To Delete", club_id=1)
    created = await category_crud.create(db_session, obj_in=data)
    item_id = created.id
    
    result = await category_crud.delete(db_session, item_id)
    assert result is True