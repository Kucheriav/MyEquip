from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.crud import ValueCRUD
from app.schemas.value_schema import ValueCreate, ValueUpdate, ValueResponse
from typing import List

router = APIRouter(prefix="/api/values", tags=["values"])
value_crud = ValueCRUD()


@router.post("/", response_model=ValueResponse, status_code=201)
async def create_value(value: ValueCreate, db: AsyncSession = Depends(get_db)):
    """Create a new value"""
    return await value_crud.create(db, obj_in=value)


@router.get("/{value_id}", response_model=ValueResponse)
async def get_value(value_id: int, db: AsyncSession = Depends(get_db)):
    """Get value by ID"""
    value = await value_crud.get(db, value_id)
    if not value:
        raise HTTPException(status_code=404, detail="Value not found")
    return value


@router.get("/parameter/{parameter_id}", response_model=List[ValueResponse])
async def get_values_by_parameter(parameter_id: int, db: AsyncSession = Depends(get_db)):
    """Get all values for a parameter"""
    return await value_crud.get_by_parameter(db, parameter_id)


@router.put("/{value_id}", response_model=ValueResponse)
async def update_value(value_id: int, value_update: ValueUpdate, db: AsyncSession = Depends(get_db)):
    """Update value"""
    db_value = await value_crud.get(db, value_id)
    if not db_value:
        raise HTTPException(status_code=404, detail="Value not found")
    return await value_crud.update(db, db_obj=db_value, obj_in=value_update)


@router.delete("/{value_id}", status_code=204)
async def delete_value(value_id: int, db: AsyncSession = Depends(get_db)):
    """Delete value"""
    if not await value_crud.delete(db, value_id):
        raise HTTPException(status_code=404, detail="Value not found")
    return None