from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import date
from typing import Optional, List

from app.database import get_db
from app.crud import BreakdownCRUD, ItemCRUD
from app.schemas.breakdown_schema import (
    BreakdownCreate, BreakdownUpdate, BreakdownResponse
)
from app.services import breakdown_service, access_service, BusinessRuleError
from app.dependencies import require_auth
from app.models import Breakdown, Item, User

router = APIRouter(prefix="/api/breakdowns", tags=["breakdowns"], dependencies=[Depends(require_auth)])
breakdown_crud = BreakdownCRUD()
item_crud = ItemCRUD()


class BreakdownRepairRequest(BaseModel):
    repairer_id: Optional[int] = None
    repaired_date: Optional[date] = None


def _handle_business_rule(e: BusinessRuleError):
    message = str(e)
    status = 404 if "not found" in message.lower() else 400
    raise HTTPException(status_code=status, detail=message)


def _get_visible_breakdown(db: Session, current_user: User | None, breakdown_id: int) -> Breakdown:
    breakdown = breakdown_crud.get(db, breakdown_id)
    if not breakdown:
        raise HTTPException(status_code=404, detail="Breakdown not found")
    item = item_crud.get(db, breakdown.item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    access_service.ensure_staff(db, current_user, item.club_id)
    return breakdown


@router.post("/", response_model=BreakdownResponse, status_code=201)
def create_breakdown(
    breakdown: BreakdownCreate,
    current_user: User | None = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """Report equipment breakdown (sets item status to 'maintenance')"""
    item = item_crud.get(db, breakdown.item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    access_service.ensure_staff(db, current_user, item.club_id)
    try:
        return breakdown_service.create_breakdown(db, data=breakdown)
    except BusinessRuleError as e:
        _handle_business_rule(e)


@router.get("/{breakdown_id}", response_model=BreakdownResponse)
def get_breakdown(
    breakdown_id: int,
    current_user: User | None = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """Get breakdown by ID"""
    return _get_visible_breakdown(db, current_user, breakdown_id)


@router.get("/", response_model=List[BreakdownResponse])
def get_all_breakdowns(
    skip: int = 0,
    limit: int = 100,
    current_user: User | None = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """Get breakdowns of your clubs"""
    query = db.query(Breakdown).join(Item, Item.id == Breakdown.item_id)
    query = access_service.filter_by_clubs(query, Item.club_id, db, current_user)
    return query.offset(skip).limit(limit).all()


@router.get("/item/{item_id}", response_model=List[BreakdownResponse])
def get_breakdowns_by_item(
    item_id: int,
    current_user: User | None = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """Get all breakdowns for an item"""
    item = item_crud.get(db, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    access_service.ensure_staff(db, current_user, item.club_id)
    return breakdown_crud.get_by_item(db, item_id)


@router.get("/unrepaired/", response_model=List[BreakdownResponse])
def get_unrepaired_breakdowns(
    current_user: User | None = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """Get unrepaired items of your clubs"""
    query = (
        db.query(Breakdown)
        .join(Item, Item.id == Breakdown.item_id)
        .filter(Breakdown.repaired_date == None)  # noqa: E711
    )
    query = access_service.filter_by_clubs(query, Item.club_id, db, current_user)
    return query.all()


@router.put("/{breakdown_id}", response_model=BreakdownResponse)
def update_breakdown(
    breakdown_id: int,
    breakdown_update: BreakdownUpdate,
    current_user: User | None = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """Update breakdown (syncs the item status when it is repaired)"""
    _get_visible_breakdown(db, current_user, breakdown_id)
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
    current_user: User | None = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """Mark a breakdown as repaired (item returns to 'available' when no open breakdowns remain)"""
    _get_visible_breakdown(db, current_user, breakdown_id)
    try:
        return breakdown_service.repair_breakdown(
            db,
            breakdown_id=breakdown_id,
            repairer_id=request.repairer_id,
            repaired_date=request.repaired_date or date.today(),
        )
    except BusinessRuleError as e:
        _handle_business_rule(e)
