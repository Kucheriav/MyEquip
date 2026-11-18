from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.crud import StorageCRUD
from app.schemas.storage_schema import StorageCreate, StorageUpdate, StorageResponse
from app.dependencies import require_auth
from app.models import Storage, User
from app.services import access_service

router = APIRouter(prefix="/api/storages", tags=["storages"], dependencies=[Depends(require_auth)])
storage_crud = StorageCRUD()


@router.post("/", response_model=StorageResponse, status_code=201)
def create_storage(
    storage: StorageCreate,
    current_user: User | None = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """Create a new storage (leader of the club only)"""
    access_service.ensure_leader(db, current_user, storage.club_id)
    return storage_crud.create(db, obj_in=storage)


@router.get("/", response_model=List[StorageResponse])
def get_all_storages(
    skip: int = 0,
    limit: int = 100,
    club_id: int | None = None,
    current_user: User | None = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """Get storages of your clubs"""
    if not access_service.auth_disabled():
        club_ids = access_service.staff_club_ids(db, current_user)
        if club_id is not None:
            if club_id not in club_ids:
                raise HTTPException(status_code=403, detail="Access denied: club is not yours")
            club_ids = {club_id}
        if not club_ids:
            return []
        return (
            db.query(Storage)
            .filter(Storage.club_id.in_(club_ids))
            .offset(skip)
            .limit(limit)
            .all()
        )
    if club_id is not None:
        return storage_crud.get_by_club(db, club_id)
    return storage_crud.get_all(db, skip=skip, limit=limit)


@router.get("/{storage_id}", response_model=StorageResponse)
def get_storage(
    storage_id: int,
    current_user: User | None = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """Get storage by ID (staff of the club only)"""
    storage = storage_crud.get(db, storage_id)
    if not storage:
        raise HTTPException(status_code=404, detail="Storage not found")
    access_service.ensure_staff(db, current_user, storage.club_id)
    return storage


@router.get("/club/{club_id}", response_model=List[StorageResponse])
def get_storages_by_club(
    club_id: int,
    current_user: User | None = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """Get all storages for a club"""
    access_service.ensure_club_visible(db, current_user, club_id)
    return storage_crud.get_by_club(db, club_id)


@router.put("/{storage_id}", response_model=StorageResponse)
def update_storage(
    storage_id: int,
    storage_update: StorageUpdate,
    current_user: User | None = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """Update storage (leader of the club only)"""
    db_storage = storage_crud.get(db, storage_id)
    if not db_storage:
        raise HTTPException(status_code=404, detail="Storage not found")
    access_service.ensure_leader(db, current_user, db_storage.club_id)
    return storage_crud.update(db, db_obj=db_storage, obj_in=storage_update)


@router.delete("/{storage_id}", status_code=204)
def delete_storage(
    storage_id: int,
    current_user: User | None = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """Delete storage (leader of the club only)"""
    db_storage = storage_crud.get(db, storage_id)
    if not db_storage:
        raise HTTPException(status_code=404, detail="Storage not found")
    access_service.ensure_leader(db, current_user, db_storage.club_id)
    if not storage_crud.delete(db, storage_id):
        raise HTTPException(status_code=404, detail="Storage not found")
    return None
