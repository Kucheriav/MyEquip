from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.crud import ItemParameterValueCRUD
from app.schemas.item_parameter_value_schema import (
    ItemParameterValueCreate, ItemParameterValueResponse
)
from app.dependencies import require_auth
from typing import List

router = APIRouter(prefix="/api/item-parameters", tags=["item-parameters"], dependencies=[Depends(require_auth)])
item_param_crud = ItemParameterValueCRUD()


@router.post("/", response_model=ItemParameterValueResponse, status_code=201)
def create_item_parameter(
    item_param: ItemParameterValueCreate,
    db: Session = Depends(get_db)
):
    """Add parameter value to an item"""
    return item_param_crud.create(db, obj_in=item_param)


@router.get("/", response_model=List[ItemParameterValueResponse])
def get_all_item_parameters(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """Get all item parameter values"""
    return item_param_crud.get_all(db, skip=skip, limit=limit)


@router.get("/{item_param_id}", response_model=ItemParameterValueResponse)
def get_item_parameter(item_param_id: int, db: Session = Depends(get_db)):
    """Get item parameter by ID"""
    item_param = item_param_crud.get(db, item_param_id)
    if not item_param:
        raise HTTPException(status_code=404, detail="Item parameter not found")
    return item_param


@router.get("/item/{item_id}", response_model=List[ItemParameterValueResponse])
def get_parameters_by_item(item_id: int, db: Session = Depends(get_db)):
    """Get all parameters for an item"""
    return item_param_crud.get_by_item(db, item_id)


@router.get("/parameter/{parameter_id}", response_model=List[ItemParameterValueResponse])
def get_items_by_parameter(parameter_id: int, db: Session = Depends(get_db)):
    """Get all items with a specific parameter"""
    return item_param_crud.get_by_parameter(db, parameter_id)


@router.delete("/{item_param_id}", status_code=204)
def delete_item_parameter(item_param_id: int, db: Session = Depends(get_db)):
    """Delete item parameter"""
    if not item_param_crud.delete(db, item_param_id):
        raise HTTPException(status_code=404, detail="Item parameter not found")
    return None