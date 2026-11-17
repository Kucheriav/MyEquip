from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.database import get_db
from app.crud import CategoryCRUD
from app.schemas.category_schema import CategoryCreate, CategoryUpdate, CategoryResponse
from app.schemas.parameter_schema import ParameterResponse
from app.services import category_parameter_service
from app.services.exceptions import BusinessRuleError
from app.dependencies import require_auth
from typing import List

router = APIRouter(prefix="/api/categories", tags=["categories"], dependencies=[Depends(require_auth)])
category_crud = CategoryCRUD()


@router.post("/", response_model=CategoryResponse, status_code=201)
def create_category(category: CategoryCreate, db: Session = Depends(get_db)):
    """Create a new category"""
    return category_crud.create(db, obj_in=category)


@router.get("/", response_model=List[CategoryResponse])
def get_all_categories(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """Get all categories"""
    return category_crud.get_all(db, skip=skip, limit=limit)


@router.get("/{category_id}", response_model=CategoryResponse)
def get_category(category_id: int, db: Session = Depends(get_db)):
    """Get category by ID"""
    category = category_crud.get(db, category_id)
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    return category


@router.get("/club/{club_id}", response_model=List[CategoryResponse])
def get_categories_by_club(club_id: int, db: Session = Depends(get_db)):
    """Get all categories for a club"""
    return category_crud.get_by_club(db, club_id)


@router.put("/{category_id}", response_model=CategoryResponse)
def update_category(category_id: int, category_update: CategoryUpdate, db: Session = Depends(get_db)):
    """Update category"""
    db_category = category_crud.get(db, category_id)
    if not db_category:
        raise HTTPException(status_code=404, detail="Category not found")
    return category_crud.update(db, db_obj=db_category, obj_in=category_update)


@router.delete("/{category_id}", status_code=204)
def delete_category(category_id: int, db: Session = Depends(get_db)):
    """Delete category"""
    if not category_crud.delete(db, category_id):
        raise HTTPException(status_code=404, detail="Category not found")
    return None


# ==================== CATEGORY PARAMETERS ====================
class EffectiveParameterResponse(ParameterResponse):
    inherited: bool  # True = came from a parent category


class AttachParameterRequest(BaseModel):
    parameter_id: int


@router.get("/{category_id}/parameters", response_model=List[EffectiveParameterResponse])
def get_category_parameters(
    category_id: int,
    include_inherited: bool = True,
    db: Session = Depends(get_db),
):
    """Parameters describing items of this category (optionally with the
    parent chain's inherited ones)."""
    category = category_crud.get(db, category_id)
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    return category_parameter_service.get_effective_parameters(
        db, category, include_inherited=include_inherited
    )


@router.post("/{category_id}/parameters", response_model=EffectiveParameterResponse, status_code=201)
def attach_parameter(category_id: int, request: AttachParameterRequest, db: Session = Depends(get_db)):
    """Attach an existing parameter to a category"""
    try:
        parameter = category_parameter_service.attach_parameter(db, category_id, request.parameter_id)
    except BusinessRuleError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {
        "id": parameter.id,
        "name": parameter.name,
        "param_type": parameter.param_type,
        "inherited": False,
    }


@router.delete("/{category_id}/parameters/{parameter_id}", status_code=204)
def detach_parameter(category_id: int, parameter_id: int, db: Session = Depends(get_db)):
    """Detach a parameter from a category"""
    try:
        category_parameter_service.detach_parameter(db, category_id, parameter_id)
    except BusinessRuleError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return None