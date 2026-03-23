from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.crud import BreakdownCRUD
from app.schemas.breakdown_schema import (
    BreakdownCreate, BreakdownUpdate, BreakdownResponse
)
from typing import List

router = APIRouter(prefix="/api/breakdowns", tags=["breakdowns"])
breakdown_crud = BreakdownCRUD()


@router.post("/", response_model=BreakdownResponse, status_code=201)
def create_breakdown(breakdown: BreakdownCreate, db: Session = Depends(get_db)):
    """Report equipment breakdown"""
    return breakdown_crud.create(db, obj_in=breakdown)


@router.get("/{breakdown_id}", response_model=BreakdownResponse)
def get_breakdown(breakdown_id: int, db: Session = Depends(get_db)):
    """Get breakdown by ID"""
    breakdown = breakdown_crud.get(db, breakdown_id)
    if not breakdown:
        raise HTTPException(status_code=404, detail="Breakdown not found")
    return breakdown


@router.get("/", response_model=List[BreakdownResponse])
def get_all_breakdowns(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """Get all breakdowns"""
    return breakdown_crud.get_all(db, skip=skip, limit=limit)


@router.get("/item/{item_id}", response_model=List[BreakdownResponse])
def get_breakdowns_by_item(item_id: int, db: Session = Depends(get_db)):
    """Get all breakdowns for an item"""
    return breakdown_crud.get_by_item(db, item_id)


@router.get("/unrepaired/", response_model=List[BreakdownResponse])
def get_unrepaired_breakdowns(db: Session = Depends(get_db)):
    """Get all unrepaired items"""
    return breakdown_crud.get_unrepaired(db)


@router.put("/{breakdown_id}", response_model=BreakdownResponse)
def update_breakdown(
    breakdown_id: int,
    breakdown_update: BreakdownUpdate,
    db: Session = Depends(get_db)
):
    """Update breakdown (e.g., mark as repaired)"""
    db_breakdown = breakdown_crud.get(db, breakdown_id)
    if not db_breakdown:
        raise HTTPException(status_code=404, detail="Breakdown not found")
    return breakdown_crud.update(db, db_obj=db_breakdown, obj_in=breakdown_update)


@router.delete("/{breakdown_id}", status_code=204)
def delete_breakdown(breakdown_id: int, db: Session = Depends(get_db)):
    """Delete breakdown record"""
    if not breakdown_crud.delete(db, breakdown_id):
        raise HTTPException(status_code=404, detail="Breakdown not found")
    return None