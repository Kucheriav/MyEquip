from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import date
from typing import Optional

from app.database import get_db
from app.crud import DistributionCRUD
from app.schemas.distribution_schema import (
    DistributionCreate, DistributionUpdate, DistributionResponse
)
from app.services import distribution_service, BusinessRuleError
from typing import List

router = APIRouter(prefix="/api/distributions", tags=["distributions"])
distribution_crud = DistributionCRUD()


class DistributionReturnRequest(BaseModel):
    accepter_id: Optional[int] = None
    accepting_date: Optional[date] = None
    comment: Optional[str] = None


def _handle_business_rule(e: BusinessRuleError):
    message = str(e)
    status = 404 if "not found" in message.lower() else 400
    raise HTTPException(status_code=status, detail=message)


@router.post("/", response_model=DistributionResponse, status_code=201)
def create_distribution(distribution: DistributionCreate, db: Session = Depends(get_db)):
    """Issue an item to a user (only 'available' items; sets item status to 'issued')"""
    try:
        return distribution_service.create_distribution(db, data=distribution)
    except BusinessRuleError as e:
        _handle_business_rule(e)


@router.get("/{distribution_id}", response_model=DistributionResponse)
def get_distribution(distribution_id: int, db: Session = Depends(get_db)):
    """Get distribution by ID"""
    distribution = distribution_crud.get(db, distribution_id)
    if not distribution:
        raise HTTPException(status_code=404, detail="Distribution not found")
    return distribution


@router.get("/", response_model=List[DistributionResponse])
def get_all_distributions(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """Get all distributions"""
    return distribution_crud.get_all(db, skip=skip, limit=limit)


@router.get("/item/{item_id}", response_model=List[DistributionResponse])
def get_distributions_by_item(item_id: int, db: Session = Depends(get_db)):
    """Get all distributions for an item"""
    return distribution_crud.get_by_item(db, item_id)


@router.get("/user-given/{user_id}", response_model=List[DistributionResponse])
def get_distributions_given_by_user(user_id: int, db: Session = Depends(get_db)):
    """Get all items given by a user"""
    return distribution_crud.get_by_user_given(db, user_id)


@router.get("/user-received/{user_id}", response_model=List[DistributionResponse])
def get_distributions_received_by_user(user_id: int, db: Session = Depends(get_db)):
    """Get all items received by a user"""
    return distribution_crud.get_by_user_received(db, user_id)


@router.get("/active/", response_model=List[DistributionResponse])
def get_active_distributions(db: Session = Depends(get_db)):
    """Get all active distributions"""
    return distribution_crud.get_active_distributions(db)


@router.put("/{distribution_id}", response_model=DistributionResponse)
def update_distribution(
    distribution_id: int,
    distribution_update: DistributionUpdate,
    db: Session = Depends(get_db)
):
    """Update distribution (syncs the item status when the status changes)"""
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
    db: Session = Depends(get_db),
):
    """Accept an item back (sets distribution to 'returned', item to 'available')"""
    try:
        return distribution_service.return_distribution(
            db,
            distribution_id=distribution_id,
            accepter_id=request.accepter_id,
            accepting_date=request.accepting_date or date.today(),
            comment=request.comment,
        )
    except BusinessRuleError as e:
        _handle_business_rule(e)
