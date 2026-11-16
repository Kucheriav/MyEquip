from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.crud import ItemCRUD
from app.schemas.item_schema import ItemCreate, ItemUpdate, ItemResponse
from app.dependencies import require_auth
from typing import List, Optional

router = APIRouter(prefix="/api/items", tags=["items"], dependencies=[Depends(require_auth)])
item_crud = ItemCRUD()


@router.post("/", response_model=ItemResponse, status_code=201)
def create_item(item: ItemCreate, db: Session = Depends(get_db)):
    """Create a new item"""
    return item_crud.create(db, obj_in=item)


@router.get("/{item_id}", response_model=ItemResponse)
def get_item(item_id: int, db: Session = Depends(get_db)):
    """Get item by ID"""
    item = item_crud.get(db, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return item


@router.get("/", response_model=List[ItemResponse])
def get_all_items(
    skip: int = 0,
    limit: int = 100,
    storage_id: Optional[int] = None,
    owner_id: Optional[int] = None,
    category_id: Optional[int] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Get items with optional filters"""
    if storage_id:
        return item_crud.get_by_storage(db, storage_id)
    elif owner_id:
        return item_crud.get_by_owner(db, owner_id)
    elif category_id:
        return item_crud.get_by_category(db, category_id)
    elif status:
        return item_crud.get_by_status(db, status)
    return item_crud.get_all(db, skip=skip, limit=limit)


@router.put("/{item_id}", response_model=ItemResponse)
def update_item(item_id: int, item_update: ItemUpdate, db: Session = Depends(get_db)):
    """Update item"""
    db_item = item_crud.get(db, item_id)
    if not db_item:
        raise HTTPException(status_code=404, detail="Item not found")
    return item_crud.update(db, db_obj=db_item, obj_in=item_update)


@router.delete("/{item_id}", status_code=204)
def delete_item(item_id: int, db: Session = Depends(get_db)):
    """Delete item"""
    if not item_crud.delete(db, item_id):
        raise HTTPException(status_code=404, detail="Item not found")
    return None