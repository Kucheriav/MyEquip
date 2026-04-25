from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.crud import UserCRUD
from app.schemas.user_schema import UserCreate, UserUpdate, UserResponse
from typing import List

router = APIRouter(prefix="/api/users", tags=["users"])
user_crud = UserCRUD()


@router.post("/", response_model=UserResponse, status_code=201)
async def create_user(user: UserCreate, db: AsyncSession = Depends(get_db)):
    """Create a new user"""
    db_user = await user_crud.get_by_email(db, email=user.email)
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    return await user_crud.create(db, obj_in=user)


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(user_id: int, db: AsyncSession = Depends(get_db)):
    """Get user by ID"""
    user = await user_crud.get(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.get("/", response_model=List[UserResponse])
async def get_all_users(skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_db)):
    """Get all users with pagination"""
    return await user_crud.get_all(db, skip=skip, limit=limit)


@router.put("/{user_id}", response_model=UserResponse)
async def update_user(user_id: int, user_update: UserUpdate, db: AsyncSession = Depends(get_db)):
    """Update user"""
    db_user = await user_crud.get(db, user_id)
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    return await user_crud.update(db, db_obj=db_user, obj_in=user_update)


@router.delete("/{user_id}", status_code=204)
async def delete_user(user_id: int, db: AsyncSession = Depends(get_db)):
    """Delete user"""
    if not await user_crud.delete(db, user_id):
        raise HTTPException(status_code=404, detail="User not found")
    return None