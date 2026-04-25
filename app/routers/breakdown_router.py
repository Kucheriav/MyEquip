from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.crud import BreakdownCRUD
from app.schemas.breakdown_schema import (
    BreakdownCreate, BreakdownUpdate, BreakdownResponse
)
from typing import List

router = APIRouter(prefix="/api/breakdowns", tags=["breakdowns"])
breakdown_crud = BreakdownCRUD()


@router.post("/", response_model=BreakdownResponse, status_code=201)
async def create_breakdown(breakdown: BreakdownCreate, db: AsyncSession = Depends(get_db)):
    """Report equipment breakdown"""
    return await breakdown_crud.create(db, obj_in=breakdown)


@router.get("/{breakdown_id}", response_model=BreakdownResponse)
async def get_breakdown(breakdown_id: int, db: AsyncSession = Depends(get_db)):
    """Get breakdown by ID"""
    breakdown = await breakdown_crud.get(db, breakdown_id)
    if not breakdown:
        raise HTTPException(status_code=404, detail="Breakdown not found")
    return breakdown


@router.get("/", response_model=List[BreakdownResponse])
async def get_all_breakdowns(skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_db)):
    """Get all breakdowns"""
    return await breakdown_crud.get_all(db, skip=skip, limit=limit)


@router.get("/item/{item_id}", response_model=List[BreakdownResponse])
async def get_breakdowns_by_item(item_id: int, db: AsyncSession = Depends(get_db)):
    """Get all breakdowns for an item"""
    return await breakdown_crud.get_by_item(db, item_id)


@router.get("/unrepaired/", response_model=List[BreakdownResponse])
async def get_unrepaired_breakdowns(db: AsyncSession = Depends(get_db)):
    """Get all unrepaired items"""
    return await breakdown_crud.get_unrepaired(db)


@router.put("/{breakdown_id}", response_model=BreakdownResponse)
async def update_breakdown(
    breakdown_id: int,
    breakdown_update: BreakdownUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Update breakdown (e.g., mark as repaired)"""
    db_breakdown = await breakdown_crud.get(db, breakdown_id)
    if not db_breakdown:
        raise HTTPException(status_code=404, detail="Breakdown not found")
    return await breakdown_crud.update(db, db_obj=db_breakdown, obj_in=breakdown_update)


@router.delete("/{breakdown_id}", status_code=204)
async def delete_breakdown(breakdown_id: int, db: AsyncSession = Depends(get_db)):
    """Delete breakdown record"""
    if not await breakdown_crud.delete(db, breakdown_id):
        raise HTTPException(status_code=404, detail="Breakdown not found")
    return None