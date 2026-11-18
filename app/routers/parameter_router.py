from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.crud import ParameterCRUD
from app.schemas.parameter_schema import ParameterCreate, ParameterUpdate, ParameterResponse
from app.dependencies import require_auth
from app.models import User
from app.services import access_service

router = APIRouter(prefix="/api/parameters", tags=["parameters"], dependencies=[Depends(require_auth)])
parameter_crud = ParameterCRUD()


@router.post("/", response_model=ParameterResponse, status_code=201)
def create_parameter(
    parameter: ParameterCreate,
    current_user: User | None = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """Create a new parameter (leaders only; parameters are global)"""
    access_service.ensure_leader_any(current_user)
    return parameter_crud.create(db, obj_in=parameter)


@router.get("/{parameter_id}", response_model=ParameterResponse)
def get_parameter(parameter_id: int, db: Session = Depends(get_db)):
    """Get parameter by ID"""
    parameter = parameter_crud.get(db, parameter_id)
    if not parameter:
        raise HTTPException(status_code=404, detail="Parameter not found")
    return parameter


@router.get("/", response_model=List[ParameterResponse])
def get_all_parameters(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """Get all parameters"""
    return parameter_crud.get_all(db, skip=skip, limit=limit)


@router.put("/{parameter_id}", response_model=ParameterResponse)
def update_parameter(
    parameter_id: int,
    parameter_update: ParameterUpdate,
    current_user: User | None = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """Update parameter (leaders only)"""
    access_service.ensure_leader_any(current_user)
    db_parameter = parameter_crud.get(db, parameter_id)
    if not db_parameter:
        raise HTTPException(status_code=404, detail="Parameter not found")
    return parameter_crud.update(db, db_obj=db_parameter, obj_in=parameter_update)


@router.delete("/{parameter_id}", status_code=204)
def delete_parameter(
    parameter_id: int,
    current_user: User | None = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """Delete parameter (leaders only)"""
    access_service.ensure_leader_any(current_user)
    if not parameter_crud.delete(db, parameter_id):
        raise HTTPException(status_code=404, detail="Parameter not found")
    return None
