from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.crud import CategoryCRUD
from app.schemas.category_schema import CategoryCreate, CategoryUpdate, CategoryResponse
from typing import List

router = APIRouter(prefix="/api/categories", tags=["categories"])
category_crud = CategoryCRUD()


@router.post("/", response_model=CategoryResponse, status_code=201)
async def create_category(category: CategoryCreate, db: AsyncSession = Depends(get_db)):
    """Create a new category"""
    return await category_crud.create(db, obj_in=category)


@router.get("/{category_id}", response_model=CategoryResponse)
async def get_category(category_id: int, db: AsyncSession = Depends(get_db)):
    """Get category by ID"""
    category = await category_crud.get(db, category_id)
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    return category


@router.get("/club/{club_id}", response_model=List[CategoryResponse])
async def get_categories_by_club(club_id: int, db: AsyncSession = Depends(get_db)):
    """Get all categories for a club"""
    return await category_crud.get_by_club(db, club_id)


@router.put("/{category_id}", response_model=CategoryResponse)
async def update_category(category_id: int, category_update: CategoryUpdate, db: AsyncSession = Depends(get_db)):
    """Update category"""
    db_category = await category_crud.get(db, category_id)
    if not db_category:
        raise HTTPException(status_code=404, detail="Category not found")
    return await category_crud.update(db, db_obj=db_category, obj_in=category_update)


@router.delete("/{category_id}", status_code=204)
async def delete_category(category_id: int, db: AsyncSession = Depends(get_db)):
    """Delete category"""
    if not await category_crud.delete(db, category_id):
        raise HTTPException(status_code=404, detail="Category not found")
    return None