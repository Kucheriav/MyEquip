from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.crud import ItemParameterValueCRUD, ItemCRUD
from app.schemas.item_parameter_value_schema import (
    ItemParameterValueCreate, ItemParameterValueResponse
)
from app.dependencies import require_auth
from app.models import ItemParameterValue, Item, User
from app.services import access_service

router = APIRouter(prefix="/api/item-parameters", tags=["item-parameters"], dependencies=[Depends(require_auth)])
item_param_crud = ItemParameterValueCRUD()
item_crud = ItemCRUD()


def _ensure_item_visible(db: Session, current_user: User | None, item_id: int) -> Item:
    item = item_crud.get(db, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    access_service.ensure_staff(db, current_user, item.club_id)
    return item


@router.post("/", response_model=ItemParameterValueResponse, status_code=201)
def create_item_parameter(
    item_param: ItemParameterValueCreate,
    current_user: User | None = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """Add parameter value to an item (staff of the item's club)"""
    _ensure_item_visible(db, current_user, item_param.item_id)
    return item_param_crud.create(db, obj_in=item_param)


@router.get("/", response_model=List[ItemParameterValueResponse])
def get_all_item_parameters(
    skip: int = 0,
    limit: int = 100,
    current_user: User | None = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """Get parameter values of items in your clubs"""
    query = db.query(ItemParameterValue).join(Item, Item.id == ItemParameterValue.item_id)
    query = access_service.filter_by_clubs(query, Item.club_id, db, current_user)
    return query.offset(skip).limit(limit).all()


@router.get("/{item_param_id}", response_model=ItemParameterValueResponse)
def get_item_parameter(
    item_param_id: int,
    current_user: User | None = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """Get item parameter by ID"""
    item_param = item_param_crud.get(db, item_param_id)
    if not item_param:
        raise HTTPException(status_code=404, detail="Item parameter not found")
    _ensure_item_visible(db, current_user, item_param.item_id)
    return item_param


@router.get("/item/{item_id}", response_model=List[ItemParameterValueResponse])
def get_parameters_by_item(
    item_id: int,
    current_user: User | None = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """Get all parameters for an item"""
    _ensure_item_visible(db, current_user, item_id)
    return item_param_crud.get_by_item(db, item_id)


@router.get("/parameter/{parameter_id}", response_model=List[ItemParameterValueResponse])
def get_items_by_parameter(
    parameter_id: int,
    current_user: User | None = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """Get all items with a specific parameter (within your clubs)"""
    query = (
        db.query(ItemParameterValue)
        .join(Item, Item.id == ItemParameterValue.item_id)
        .filter(ItemParameterValue.parameter_id == parameter_id)
    )
    query = access_service.filter_by_clubs(query, Item.club_id, db, current_user)
    return query.all()


@router.delete("/{item_param_id}", status_code=204)
def delete_item_parameter(
    item_param_id: int,
    current_user: User | None = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """Delete item parameter (staff of the item's club)"""
    item_param = item_param_crud.get(db, item_param_id)
    if not item_param:
        raise HTTPException(status_code=404, detail="Item parameter not found")
    _ensure_item_visible(db, current_user, item_param.item_id)
    if not item_param_crud.delete(db, item_param_id):
        raise HTTPException(status_code=404, detail="Item parameter not found")
    return None
