from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.crud import ItemParameterValueCRUD
from app.schemas.item_parameter_value_schema import (
    ItemParameterValueCreate, ItemParameterValueResponse
)
from typing import List

router = APIRouter(prefix="/api/item-parameters", tags=["item-parameters"])
item_param_crud = ItemParameterValueCRUD()


@router.post("/", response_model=ItemParameterValueResponse, status_code=201)
async def create_item_parameter(
    item_param: ItemParameterValueCreate,
    db: AsyncSession = Depends(get_db)
):
    """Add parameter value to an item"""
    return await item_param_crud.create(db, obj_in=item_param)


@router.get("/{item_param_id}", response_model=ItemParameterValueResponse)
async def get_item_parameter(item_param_id: int, db: AsyncSession = Depends(get_db)):
    """Get item parameter by ID"""
    item_param = await item_param_crud.get(db, item_param_id)
    if not item_param:
        raise HTTPException(status_code=404, detail="Item parameter not found")
    return item_param


@router.get("/item/{item_id}", response_model=List[ItemParameterValueResponse])
async def get_parameters_by_item(item_id: int, db: AsyncSession = Depends(get_db)):
    """Get all parameters for an item"""
    return await item_param_crud.get_by_item(db, item_id)


@router.get("/parameter/{parameter_id}", response_model=List[ItemParameterValueResponse])
async def get_items_by_parameter(parameter_id: int, db: AsyncSession = Depends(get_db)):
    """Get all items with a specific parameter"""
    return await item_param_crud.get_by_parameter(db, parameter_id)


@router.delete("/{item_param_id}", status_code=204)
async def delete_item_parameter(item_param_id: int, db: AsyncSession = Depends(get_db)):
    """Delete item parameter"""
    if not await item_param_crud.delete(db, item_param_id):
        raise HTTPException(status_code=404, detail="Item parameter not found")
    return None