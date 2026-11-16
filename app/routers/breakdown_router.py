from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import date
from typing import Optional

from app.database import get_db
from app.crud import BreakdownCRUD
from app.schemas.breakdown_schema import (
    BreakdownCreate, BreakdownUpdate, BreakdownResponse
)
from app.services import breakdown_service, BusinessRuleError
from typing import List

router = APIRouter(prefix="/api/breakdowns", tags=["breakdowns"])
breakdown_crud = BreakdownCRUD()


class BreakdownRepairRequest(BaseModel):
    repairer_id: Optional[int] = None
    repaired_date: Optional[date] = None


def _handle_business_rule(e: BusinessRuleError):
    message = str(e)
    status = 404 if "not found" in message.lower() else 400
    raise HTTPException(status_code=status, detail=message)


@router.post("/", response_model=BreakdownResponse, status_code=201)
def create_breakdown(breakdown: BreakdownCreate, db: Session = Depends(get_db)):
    """Report equipment breakdown (sets item status to 'maintenance')"""
    try:
        return breakdown_service.create_breakdown(db, data=breakdown)
    except BusinessRuleError as e:
        _handle_business_rule(e)


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
    """Update breakdown (syncs the item status when it is repaired)"""
    try:
        return breakdown_service.update_breakdown(
            db, breakdown_id=breakdown_id, data=breakdown_update
        )
    except BusinessRuleError as e:
        _handle_business_rule(e)


@router.post("/{breakdown_id}/repair", response_model=BreakdownResponse)
def repair_breakdown(
    breakdown_id: int,
    request: BreakdownRepairRequest,
    db: Session = Depends(get_db),
):
    """Mark a breakdown as repaired (item returns to 'available' when no open breakdowns remain)"""
    try:
        return breakdown_service.repair_breakdown(
            db,
            breakdown_id=breakdown_id,
            repairer_id=request.repairer_id,
            repaired_date=request.repaired_date or date.today(),
        )
    except BusinessRuleError as e:
        _handle_business_rule(e)
