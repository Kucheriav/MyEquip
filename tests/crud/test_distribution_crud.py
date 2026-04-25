import pytest
from datetime import date, timedelta
from app.crud.distribution_crud import distribution_crud
from app.schemas.distribution_schema import DistributionCreate


@pytest.mark.asyncio
async def test_create_distribution(db_session):
    dist_data = DistributionCreate(
        item_id=1,
        giver_id=1,
        getter_id=2,
        distribution_date=date.today(),
        status="issued"
    )
    result = await distribution_crud.create(db_session, obj_in=dist_data)
    
    assert result.item_id == 1
    assert result.giver_id == 1
    assert result.getter_id == 2
    assert result.status == "issued"
    assert result.id is not None


@pytest.mark.asyncio
async def test_get_by_item(db_session):
    dist_data = DistributionCreate(
        item_id=1,
        giver_id=1,
        getter_id=2,
        distribution_date=date.today()
    )
    await distribution_crud.create(db_session, obj_in=dist_data)
    
    result = await distribution_crud.get_by_item(db_session, 1)
    
    assert len(result) == 1
    assert result[0].item_id == 1


@pytest.mark.asyncio
async def test_get_active_distributions(db_session):
    dist_data = DistributionCreate(
        item_id=1,
        giver_id=1,
        getter_id=2,
        distribution_date=date.today(),
        status="issued"
    )
    await distribution_crud.create(db_session, obj_in=dist_data)
    
    result = await distribution_crud.get_active_distributions(db_session)
    
    assert len(result) == 1
    assert result[0].status == "issued"


@pytest.mark.asyncio
async def test_get_overdue_distributions(db_session):
    yesterday = date.today() - timedelta(days=1)
    dist_data = DistributionCreate(
        item_id=1,
        giver_id=1,
        getter_id=2,
        distribution_date=yesterday,
        expiration_date=yesterday,
        status="issued"
    )
    await distribution_crud.create(db_session, obj_in=dist_data)
    
    result = await distribution_crud.get_overdue_distributions(db_session, date.today())
    
    assert len(result) == 1
    assert result[0].expiration_date < date.today()