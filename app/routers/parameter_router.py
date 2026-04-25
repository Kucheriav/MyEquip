from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.crud import ParameterCRUD
from app.schemas.parameter_schema import ParameterCreate, ParameterUpdate, ParameterResponse
from typing import List

router = APIRouter(prefix="/api/parameters", tags=["parameters"])
parameter_crud = ParameterCRUD()


@router.post("/", response_model=ParameterResponse, status_code=201)
async def create_parameter(parameter: ParameterCreate, db: AsyncSession = Depends(get_db)):
    """Create a new parameter"""
    return await parameter_crud.create(db, obj_in=parameter)


@router.get("/{parameter_id}", response_model=ParameterResponse)
async def get_parameter(parameter_id: int, db: AsyncSession = Depends(get_db)):
    """Get parameter by ID"""
    parameter = await parameter_crud.get(db, parameter_id)
    if not parameter:
        raise HTTPException(status_code=404, detail="Parameter not found")
    return parameter


@router.get("/", response_model=List[ParameterResponse])
async def get_all_parameters(skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_db)):
    """Get all parameters"""
    return await parameter_crud.get_all(db, skip=skip, limit=limit)


@router.put("/{parameter_id}", response_model=ParameterResponse)
async def update_parameter(parameter_id: int, parameter_update: ParameterUpdate, db: AsyncSession = Depends(get_db)):
    """Update parameter"""
    db_parameter = await parameter_crud.get(db, parameter_id)
    if not db_parameter:
        raise HTTPException(status_code=404, detail="Parameter not found")
    return await parameter_crud.update(db, db_obj=db_parameter, obj_in=parameter_update)


@router.delete("/{parameter_id}", status_code=204)
async def delete_parameter(parameter_id: int, db: AsyncSession = Depends(get_db)):
    """Delete parameter"""
    if not await parameter_crud.delete(db, parameter_id):
        raise HTTPException(status_code=404, detail="Parameter not found")
    return None