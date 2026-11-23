import pytest
from app.crud.item_crud import item_crud
from app.schemas.item_schema import ItemCreate


@pytest.mark.asyncio
async def test_create_item(db_session):
    item_data = ItemCreate(
        name="Test Item",
        category_id=1,
        storage_id=1,
        owner_id=1,
        status="available"
    )
    result = await item_crud.create(db_session, obj_in=item_data)
    
    assert result.name == "Test Item"
    assert result.category_id == 1
    assert result.storage_id == 1
    assert result.owner_id == 1
    assert result.status == "available"
    assert result.id is not None


@pytest.mark.asyncio
async def test_get_item(db_session):
    item_data = ItemCreate(
        name="Test Item",
        category_id=1,
        storage_id=1,
        owner_id=1
    )
    created = await item_crud.create(db_session, obj_in=item_data)
    
    result = await item_crud.get(db_session, created.id)
    
    assert result is not None
    assert result.name == "Test Item"


@pytest.mark.asyncio
async def test_get_item_not_found(db_session):
    result = await item_crud.get(db_session, 999)
    
    assert result is None


@pytest.mark.asyncio
async def test_get_all_items(db_session):
    for i in range(3):
        item_data = ItemCreate(
            name=f"Item {i}",
            category_id=1,
            storage_id=1,
            owner_id=1
        )
        await item_crud.create(db_session, obj_in=item_data)
    
    result = await item_crud.get_all(db_session)
    
    assert len(result) == 3


@pytest.mark.asyncio
async def test_update_item(db_session):
    item_data = ItemCreate(
        name="Original Name",
        category_id=1,
        storage_id=1,
        owner_id=1
    )
    created = await item_crud.create(db_session, obj_in=item_data)
    
    from app.schemas.item_schema import ItemUpdate
    update_data = ItemUpdate(name="Updated Name")
    result = await item_crud.update(db_session, db_obj=created, obj_in=update_data)
    
    assert result.name == "Updated Name"


@pytest.mark.asyncio
async def test_delete_item(db_session):
    item_data = ItemCreate(
        name="To Delete",
        category_id=1,
        storage_id=1,
        owner_id=1
    )
    created = await item_crud.create(db_session, obj_in=item_data)
    item_id = created.id
    
    result = await item_crud.delete(db_session, item_id)
    
    assert result is True
    assert await item_crud.get(db_session, item_id) is None