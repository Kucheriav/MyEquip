from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.crud import StorageCRUD
from app.schemas.storage_schema import StorageCreate, StorageUpdate, StorageResponse
from typing import List

router = APIRouter(prefix="/api/storages", tags=["storages"])
storage_crud = StorageCRUD()


@router.post("/", response_model=StorageResponse, status_code=201)
async def create_storage(storage: StorageCreate, db: AsyncSession = Depends(get_db)):
    """Create a new storage"""
    return await storage_crud.create(db, obj_in=storage)


@router.get("/{storage_id}", response_model=StorageResponse)
async def get_storage(storage_id: int, db: AsyncSession = Depends(get_db)):
    """Get storage by ID"""
    storage = await storage_crud.get(db, storage_id)
    if not storage:
        raise HTTPException(status_code=404, detail="Storage not found")
    return storage


@router.get("/club/{club_id}", response_model=List[StorageResponse])
async def get_storages_by_club(club_id: int, db: AsyncSession = Depends(get_db)):
    """Get all storages for a club"""
    return await storage_crud.get_by_club(db, club_id)


@router.put("/{storage_id}", response_model=StorageResponse)
async def update_storage(storage_id: int, storage_update: StorageUpdate, db: AsyncSession = Depends(get_db)):
    """Update storage"""
    db_storage = await storage_crud.get(db, storage_id)
    if not db_storage:
        raise HTTPException(status_code=404, detail="Storage not found")
    return await storage_crud.update(db, db_obj=db_storage, obj_in=storage_update)


@router.delete("/{storage_id}", status_code=204)
async def delete_storage(storage_id: int, db: AsyncSession = Depends(get_db)):
    """Delete storage"""
    if not await storage_crud.delete(db, storage_id):
        raise HTTPException(status_code=404, detail="Storage not found")
    return None