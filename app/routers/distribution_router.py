from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.crud import DistributionCRUD
from app.schemas.distribution_schema import (
    DistributionCreate, DistributionUpdate, DistributionResponse
)
from typing import List
from datetime import date

router = APIRouter(prefix="/api/distributions", tags=["distributions"])
distribution_crud = DistributionCRUD()


@router.post("/", response_model=DistributionResponse, status_code=201)
async def create_distribution(distribution: DistributionCreate, db: AsyncSession = Depends(get_db)):
    """Issue an item to a user"""
    return await distribution_crud.create(db, obj_in=distribution)


@router.get("/{distribution_id}", response_model=DistributionResponse)
async def get_distribution(distribution_id: int, db: AsyncSession = Depends(get_db)):
    """Get distribution by ID"""
    distribution = await distribution_crud.get(db, distribution_id)
    if not distribution:
        raise HTTPException(status_code=404, detail="Distribution not found")
    return distribution


@router.get("/", response_model=List[DistributionResponse])
async def get_all_distributions(skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_db)):
    """Get all distributions"""
    return await distribution_crud.get_all(db, skip=skip, limit=limit)


@router.get("/item/{item_id}", response_model=List[DistributionResponse])
async def get_distributions_by_item(item_id: int, db: AsyncSession = Depends(get_db)):
    """Get all distributions for an item"""
    return await distribution_crud.get_by_item(db, item_id)


@router.get("/user-given/{user_id}", response_model=List[DistributionResponse])
async def get_distributions_given_by_user(user_id: int, db: AsyncSession = Depends(get_db)):
    """Get all items given by a user"""
    return await distribution_crud.get_by_user_given(db, user_id)


@router.get("/user-received/{user_id}", response_model=List[DistributionResponse])
async def get_distributions_received_by_user(user_id: int, db: AsyncSession = Depends(get_db)):
    """Get all items received by a user"""
    return await distribution_crud.get_by_user_received(db, user_id)


@router.get("/active/", response_model=List[DistributionResponse])
async def get_active_distributions(db: AsyncSession = Depends(get_db)):
    """Get all active distributions"""
    return await distribution_crud.get_active_distributions(db)


@router.put("/{distribution_id}", response_model=DistributionResponse)
async def update_distribution(
    distribution_id: int,
    distribution_update: DistributionUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Update distribution (e.g., mark as returned)"""
    db_distribution = await distribution_crud.get(db, distribution_id)
    if not db_distribution:
        raise HTTPException(status_code=404, detail="Distribution not found")
    return await distribution_crud.update(db, db_obj=db_distribution, obj_in=distribution_update)