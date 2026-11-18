from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.crud import CategoryCRUD
from app.schemas.category_schema import CategoryCreate, CategoryUpdate, CategoryResponse
from app.schemas.parameter_schema import ParameterResponse
from app.services import category_parameter_service, access_service
from app.services.exceptions import BusinessRuleError
from app.dependencies import require_auth
from app.models import Category, User

router = APIRouter(prefix="/api/categories", tags=["categories"], dependencies=[Depends(require_auth)])
category_crud = CategoryCRUD()


def _get_visible_category(db: Session, current_user: User | None, category_id: int) -> Category:
    category = category_crud.get(db, category_id)
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    access_service.ensure_club_visible(db, current_user, category.club_id)
    return category


@router.post("/", response_model=CategoryResponse, status_code=201)
def create_category(
    category: CategoryCreate,
    current_user: User | None = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """Create a new category (leader of the club only)"""
    access_service.ensure_leader(db, current_user, category.club_id)
    if category.parent_id is not None:
        parent = category_crud.get(db, category.parent_id)
        if not parent:
            raise HTTPException(status_code=404, detail="Parent category not found")
        if parent.club_id != category.club_id:
            raise HTTPException(status_code=400, detail="Parent category belongs to another club")
    return category_crud.create(db, obj_in=category)


@router.get("/", response_model=List[CategoryResponse])
def get_all_categories(
    skip: int = 0,
    limit: int = 100,
    club_id: int | None = None,
    current_user: User | None = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """Get categories of your clubs"""
    if not access_service.auth_disabled():
        club_ids = access_service.staff_club_ids(db, current_user)
        if club_id is not None:
            if club_id not in club_ids:
                raise HTTPException(status_code=403, detail="Access denied: club is not yours")
            club_ids = {club_id}
        if not club_ids:
            return []
        return (
            db.query(Category)
            .filter(Category.club_id.in_(club_ids))
            .offset(skip)
            .limit(limit)
            .all()
        )
    if club_id is not None:
        return category_crud.get_by_club(db, club_id)
    return category_crud.get_all(db, skip=skip, limit=limit)


@router.get("/{category_id}", response_model=CategoryResponse)
def get_category(
    category_id: int,
    current_user: User | None = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """Get category by ID"""
    return _get_visible_category(db, current_user, category_id)


@router.get("/club/{club_id}", response_model=List[CategoryResponse])
def get_categories_by_club(
    club_id: int,
    current_user: User | None = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """Get all categories for a club"""
    access_service.ensure_club_visible(db, current_user, club_id)
    return category_crud.get_by_club(db, club_id)


@router.put("/{category_id}", response_model=CategoryResponse)
def update_category(
    category_id: int,
    category_update: CategoryUpdate,
    current_user: User | None = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """Update category (leader of the club only)"""
    db_category = _get_visible_category(db, current_user, category_id)
    access_service.ensure_leader(db, current_user, db_category.club_id)
    if category_update.parent_id is not None:
        parent = category_crud.get(db, category_update.parent_id)
        if not parent:
            raise HTTPException(status_code=404, detail="Parent category not found")
        if parent.club_id != db_category.club_id:
            raise HTTPException(status_code=400, detail="Parent category belongs to another club")
        if parent.id == category_id:
            raise HTTPException(status_code=400, detail="A category cannot be its own parent")
    return category_crud.update(db, db_obj=db_category, obj_in=category_update)


@router.delete("/{category_id}", status_code=204)
def delete_category(
    category_id: int,
    current_user: User | None = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """Delete category (leader of the club only)"""
    db_category = _get_visible_category(db, current_user, category_id)
    access_service.ensure_leader(db, current_user, db_category.club_id)
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
    current_user: User | None = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """Parameters describing items of this category (optionally with the
    parent chain's inherited ones)."""
    _get_visible_category(db, current_user, category_id)
    category = category_crud.get(db, category_id)
    return category_parameter_service.get_effective_parameters(
        db, category, include_inherited=include_inherited
    )


@router.post("/{category_id}/parameters", response_model=EffectiveParameterResponse, status_code=201)
def attach_parameter(
    category_id: int,
    request: AttachParameterRequest,
    current_user: User | None = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """Attach an existing parameter to a category (leader of the club only)"""
    category = _get_visible_category(db, current_user, category_id)
    access_service.ensure_leader(db, current_user, category.club_id)
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
def detach_parameter(
    category_id: int,
    parameter_id: int,
    current_user: User | None = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """Detach a parameter from a category (leader of the club only)"""
    category = _get_visible_category(db, current_user, category_id)
    access_service.ensure_leader(db, current_user, category.club_id)
    try:
        category_parameter_service.detach_parameter(db, category_id, parameter_id)
    except BusinessRuleError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return None
