from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import date
from typing import Optional, List

from app.database import get_db
from app.crud import DistributionCRUD, ItemCRUD
from app.crud.user_crud import user_crud
from app.schemas.distribution_schema import (
    DistributionCreate, DistributionUpdate, DistributionResponse
)
from app.services import distribution_service, access_service, BusinessRuleError
from app.dependencies import require_auth
from app.models import Distribution, Item, User

router = APIRouter(prefix="/api/distributions", tags=["distributions"], dependencies=[Depends(require_auth)])
distribution_crud = DistributionCRUD()
item_crud = ItemCRUD()


class DistributionReturnRequest(BaseModel):
    accepter_id: Optional[int] = None
    accepting_date: Optional[date] = None
    comment: Optional[str] = None
    # Storage the item is put back into; None = keep the current one
    storage_id: Optional[int] = None


def _handle_business_rule(e: BusinessRuleError):
    message = str(e)
    status = 404 if "not found" in message.lower() else 400
    raise HTTPException(status_code=status, detail=message)


def _get_visible_distribution(db: Session, current_user: User | None, distribution_id: int) -> Distribution:
    distribution = distribution_crud.get(db, distribution_id)
    if not distribution:
        raise HTTPException(status_code=404, detail="Distribution not found")
    item = item_crud.get(db, distribution.item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    access_service.ensure_staff(db, current_user, item.club_id)
    return distribution


@router.post("/", response_model=DistributionResponse, status_code=201)
def create_distribution(
    distribution: DistributionCreate,
    current_user: User | None = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """Issue an item to a user (only 'available' items; sets item status to 'issued')"""
    item = item_crud.get(db, distribution.item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    access_service.ensure_staff(db, current_user, item.club_id)

    # Only club staff may hand equipment out; a tourist is a client.
    if not access_service.is_staff_member(db, distribution.giver_id, item.club_id):
        raise HTTPException(
            status_code=400,
            detail="The giver must be a leader or storekeeper of this club",
        )
    if not access_service.is_club_member(db, distribution.getter_id, item.club_id):
        raise HTTPException(status_code=400, detail="The getter is not a member of this club")

    try:
        return distribution_service.create_distribution(db, data=distribution)
    except BusinessRuleError as e:
        _handle_business_rule(e)


@router.get("/{distribution_id}", response_model=DistributionResponse)
def get_distribution(
    distribution_id: int,
    current_user: User | None = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """Get distribution by ID"""
    return _get_visible_distribution(db, current_user, distribution_id)


@router.get("/", response_model=List[DistributionResponse])
def get_all_distributions(
    skip: int = 0,
    limit: int = 100,
    current_user: User | None = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """Get distributions of your clubs"""
    query = db.query(Distribution).join(Item, Item.id == Distribution.item_id)
    query = access_service.filter_by_clubs(query, Item.club_id, db, current_user)
    return query.offset(skip).limit(limit).all()


@router.get("/item/{item_id}", response_model=List[DistributionResponse])
def get_distributions_by_item(
    item_id: int,
    current_user: User | None = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """Get all distributions for an item"""
    item = item_crud.get(db, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    access_service.ensure_staff(db, current_user, item.club_id)
    return distribution_crud.get_by_item(db, item_id)


@router.get("/user-given/{user_id}", response_model=List[DistributionResponse])
def get_distributions_given_by_user(
    user_id: int,
    current_user: User | None = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """Get all items given by a user (within your clubs)"""
    query = (
        db.query(Distribution)
        .join(Item, Item.id == Distribution.item_id)
        .filter(Distribution.giver_id == user_id)
    )
    query = access_service.filter_by_clubs(query, Item.club_id, db, current_user)
    return query.all()


@router.get("/user-received/{user_id}", response_model=List[DistributionResponse])
def get_distributions_received_by_user(
    user_id: int,
    current_user: User | None = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """Get all items received by a user (within your clubs)"""
    query = (
        db.query(Distribution)
        .join(Item, Item.id == Distribution.item_id)
        .filter(Distribution.getter_id == user_id)
    )
    query = access_service.filter_by_clubs(query, Item.club_id, db, current_user)
    return query.all()


@router.get("/active/", response_model=List[DistributionResponse])
def get_active_distributions(
    current_user: User | None = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """Get all active distributions of your clubs"""
    query = (
        db.query(Distribution)
        .join(Item, Item.id == Distribution.item_id)
        .filter(Distribution.status == "issued")
    )
    query = access_service.filter_by_clubs(query, Item.club_id, db, current_user)
    return query.all()


@router.put("/{distribution_id}", response_model=DistributionResponse)
def update_distribution(
    distribution_id: int,
    distribution_update: DistributionUpdate,
    current_user: User | None = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """Update distribution (syncs the item status when the status changes)"""
    distribution = _get_visible_distribution(db, current_user, distribution_id)
    if distribution_update.accepter_id is not None:
        item = item_crud.get(db, distribution.item_id)
        if item and not access_service.is_staff_member(
                db, distribution_update.accepter_id, item.club_id):
            raise HTTPException(
                status_code=400,
                detail="The accepter must be a leader or storekeeper of this club",
            )
    try:
        return distribution_service.update_distribution(
            db, distribution_id=distribution_id, data=distribution_update
        )
    except BusinessRuleError as e:
        _handle_business_rule(e)


@router.post("/{distribution_id}/return", response_model=DistributionResponse)
def return_distribution(
    distribution_id: int,
    request: DistributionReturnRequest,
    current_user: User | None = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """Accept an item back (sets distribution to 'returned', item to
    'available'). The item may be put into another storage of the same
    club; that movement is recorded in the transfer history."""
    distribution = _get_visible_distribution(db, current_user, distribution_id)
    if request.accepter_id is not None:
        item = item_crud.get(db, distribution.item_id)
        if item and not access_service.is_staff_member(
                db, request.accepter_id, item.club_id):
            raise HTTPException(
                status_code=400,
                detail="The accepter must be a leader or storekeeper of this club",
            )
    try:
        return distribution_service.return_distribution(
            db,
            distribution_id=distribution_id,
            accepter_id=request.accepter_id,
            accepting_date=request.accepting_date or date.today(),
            comment=request.comment,
            storage_id=request.storage_id,
        )
    except BusinessRuleError as e:
        _handle_business_rule(e)
