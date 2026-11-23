from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import or_
from sqlalchemy.orm import Session
from typing import List, Optional

from app.database import get_db
from app.crud import ItemCRUD, CategoryCRUD, StorageCRUD
from app.schemas.item_schema import ItemCreate, ItemUpdate, ItemResponse
from app.dependencies import require_auth
from app.models import Item, User
from app.services import access_service

router = APIRouter(prefix="/api/items", tags=["items"], dependencies=[Depends(require_auth)])
item_crud = ItemCRUD()
category_crud = CategoryCRUD()
storage_crud = StorageCRUD()


def _resolve_item_club(db: Session, category_id: int, storage_id: int) -> int:
    """An item's club is defined by its category and storage, which must
    belong to the same club."""
    category = category_crud.get(db, category_id)
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    storage = storage_crud.get(db, storage_id)
    if not storage:
        raise HTTPException(status_code=404, detail="Storage not found")
    if category.club_id != storage.club_id:
        raise HTTPException(
            status_code=400,
            detail="Category and storage belong to different clubs",
        )
    return category.club_id


def _get_visible_item(db: Session, current_user: User | None, item_id: int) -> Item:
    item = item_crud.get(db, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    access_service.ensure_staff(db, current_user, item.club_id)
    return item


@router.post("/", response_model=ItemResponse, status_code=201)
def create_item(
    item: ItemCreate,
    current_user: User | None = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """Create a new item (staff of the club; the club is fixed forever)."""
    club_id = _resolve_item_club(db, item.category_id, item.storage_id)
    access_service.ensure_staff(db, current_user, club_id)

    db_item = Item(club_id=club_id, **item.model_dump())
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item


@router.get("/{item_id}", response_model=ItemResponse)
def get_item(
    item_id: int,
    current_user: User | None = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """Get item by ID (staff of the item's club)"""
    return _get_visible_item(db, current_user, item_id)


@router.get("/", response_model=List[ItemResponse])
def get_all_items(
    skip: int = 0,
    limit: int = 100,
    storage_id: Optional[int] = None,
    club_id: Optional[int] = None,
    category_id: Optional[int] = None,
    status: Optional[str] = None,
    q: Optional[str] = None,
    current_user: User | None = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """Get items of your clubs with optional filters"""
    query = db.query(Item)

    if not access_service.auth_disabled():
        club_ids = access_service.staff_club_ids(db, current_user)
        if club_id is not None:
            if club_id not in club_ids:
                raise HTTPException(status_code=403, detail="Access denied: club is not yours")
            club_ids = {club_id}
        if not club_ids:
            return []
        query = query.filter(Item.club_id.in_(club_ids))

    if storage_id:
        query = query.filter(Item.storage_id == storage_id)
    if club_id:
        query = query.filter(Item.club_id == club_id)
    if category_id:
        query = query.filter(Item.category_id == category_id)
    if status:
        query = query.filter(Item.status == status)
    if q and q.strip():
        pattern = f"%{q.strip()}%"
        query = query.filter(
            or_(Item.name.ilike(pattern), Item.serial_number.ilike(pattern))
        )

    return query.order_by(Item.id).offset(skip).limit(limit).all()


@router.put("/{item_id}", response_model=ItemResponse)
def update_item(
    item_id: int,
    item_update: ItemUpdate,
    current_user: User | None = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """Update item (staff of the club; the owning club never changes)"""
    db_item = _get_visible_item(db, current_user, item_id)

    data = item_update.model_dump(exclude_unset=True)
    if "category_id" in data:
        club_id = _resolve_item_club(db, data["category_id"], db_item.storage_id)
        if club_id != db_item.club_id:
            raise HTTPException(status_code=400, detail="An item cannot change its club")

    return item_crud.update(db, db_obj=db_item, obj_in=item_update)


@router.delete("/{item_id}", status_code=204)
def delete_item(
    item_id: int,
    current_user: User | None = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """Delete item (leader of the club only; storekeepers cannot)"""
    db_item = _get_visible_item(db, current_user, item_id)
    access_service.ensure_leader(db, current_user, db_item.club_id)
    if not item_crud.delete(db, item_id):
        raise HTTPException(status_code=404, detail="Item not found")
    return None
