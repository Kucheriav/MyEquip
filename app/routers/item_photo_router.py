"""Item photos: upload, list, serve and delete.

Access mirrors the rest of the API: only leaders and storekeepers of the
item's club may see or manage its photos. Files are never served from a
public static mount, so a photo id alone does not reveal an image.
"""
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import func
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.dependencies import require_auth
from app.models import Item, ItemPhoto, User
from app.schemas.item_photo_schema import ItemPhotoResponse
from app.services import access_service, photo_service

router = APIRouter(
    prefix="/api/item-photos", tags=["item-photos"],
    dependencies=[Depends(require_auth)],
)


def _visible_item(db: Session, current_user: User | None, item_id: int) -> Item:
    item = db.query(Item).filter(Item.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    access_service.ensure_staff(db, current_user, item.club_id)
    return item


def _visible_photo(db: Session, current_user: User | None, photo_id: int) -> ItemPhoto:
    photo = db.query(ItemPhoto).filter(ItemPhoto.id == photo_id).first()
    if not photo:
        raise HTTPException(status_code=404, detail="Photo not found")
    _visible_item(db, current_user, photo.item_id)
    return photo


@router.get("/covers")
def get_covers(
    current_user: User | None = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """First photo of every item of the user's clubs (for list previews)."""
    query = (
        db.query(ItemPhoto.item_id, func.min(ItemPhoto.id).label("photo_id"))
        .join(Item, Item.id == ItemPhoto.item_id)
    )
    if not access_service.auth_disabled():
        club_ids = access_service.staff_club_ids(db, current_user)
        if not club_ids:
            return []
        query = query.filter(Item.club_id.in_(club_ids))
    rows = query.group_by(ItemPhoto.item_id).all()
    return [{"item_id": row[0], "photo_id": row[1]} for row in rows]


@router.get("/item/{item_id}", response_model=List[ItemPhotoResponse])
def get_photos(
    item_id: int,
    current_user: User | None = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """Photos of one item, oldest first (the first one is the cover)."""
    _visible_item(db, current_user, item_id)
    return (
        db.query(ItemPhoto)
        .filter(ItemPhoto.item_id == item_id)
        .order_by(ItemPhoto.id)
        .all()
    )


@router.post("/item/{item_id}", response_model=ItemPhotoResponse, status_code=201)
async def upload_photo(
    item_id: int,
    file: UploadFile = File(...),
    current_user: User | None = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """Attach a JPEG, PNG or WebP image to an item."""
    _visible_item(db, current_user, item_id)

    limit = photo_service.max_photo_bytes()
    data = await file.read(limit + 1)
    if not data:
        raise HTTPException(status_code=400, detail="The file is empty")
    if len(data) > limit:
        raise HTTPException(status_code=413, detail="Photo is too large")

    detected = photo_service.detect_image(data)
    if detected is None:
        raise HTTPException(
            status_code=400,
            detail="Only JPEG, PNG and WebP images are supported",
        )
    extension, content_type = detected

    existing = (
        db.query(ItemPhoto).filter(ItemPhoto.item_id == item_id).count()
    )
    if existing >= photo_service.max_per_item():
        raise HTTPException(
            status_code=400, detail="Too many photos for this item")

    relative_path = photo_service.save_photo(item_id, data, extension)
    try:
        photo = ItemPhoto(
            item_id=item_id,
            file_path=relative_path,
            original_name=(file.filename or "")[:255] or None,
            content_type=content_type,
            size=len(data),
            uploaded_by=getattr(current_user, "id", None),
        )
        db.add(photo)
        db.commit()
        db.refresh(photo)
    except Exception:
        db.rollback()
        photo_service.unlink([relative_path])
        raise
    return photo


@router.get("/{photo_id}/file")
def get_photo_file(
    photo_id: int,
    current_user: User | None = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """Stream the image itself (access-checked, never cached publicly)."""
    photo = _visible_photo(db, current_user, photo_id)
    path = photo_service.photo_path(photo.file_path)
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Photo file not found")
    return FileResponse(
        path,
        media_type=photo.content_type,
        headers={
            "Cache-Control": "private, max-age=300",
            "X-Content-Type-Options": "nosniff",
        },
    )


@router.delete("/{photo_id}", status_code=204)
def delete_photo(
    photo_id: int,
    current_user: User | None = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """Remove a photo (staff of the item's club)."""
    photo = _visible_photo(db, current_user, photo_id)
    relative_path = photo.file_path
    db.delete(photo)
    db.commit()
    photo_service.unlink([relative_path])
    return None
