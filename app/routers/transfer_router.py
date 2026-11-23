from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.crud.transfer_crud import transfer_crud
from app.crud.item_crud import item_crud
from app.crud.storage_crud import storage_crud
from app.schemas.transfer_schema import TransferCreate, TransferResponse
from app.services import transfer_service, access_service, BusinessRuleError
from app.dependencies import require_auth
from app.models import Transfer, Item, User

router = APIRouter(prefix="/api/transfers", tags=["transfers"], dependencies=[Depends(require_auth)])


def _handle_business_rule(e: BusinessRuleError):
    message = str(e)
    status = 404 if "not found" in message.lower() else 400
    raise HTTPException(status_code=status, detail=message)


def _get_visible_transfer(db: Session, current_user: User | None, transfer_id: int) -> Transfer:
    transfer = transfer_crud.get(db, transfer_id)
    if not transfer:
        raise HTTPException(status_code=404, detail="Transfer not found")
    item = item_crud.get(db, transfer.item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    access_service.ensure_staff(db, current_user, item.club_id)
    return transfer


@router.post("/", response_model=TransferResponse, status_code=201)
def create_transfer(
    transfer: TransferCreate,
    current_user: User | None = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """Move an item between storages of its own club (updates the item's
    storage and keeps history)"""
    item = item_crud.get(db, transfer.item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    access_service.ensure_staff(db, current_user, item.club_id)

    # The people named in the movement log must be club staff
    for field, value in (("mover_id", transfer.mover_id),
                         ("receiver_id", transfer.receiver_id)):
        if value is not None and not access_service.is_staff_member(
                db, value, item.club_id):
            raise HTTPException(
                status_code=400,
                detail=f"The {field.replace('_id', '')} must be a leader or storekeeper of this club",
            )

    from_storage = storage_crud.get(db, transfer.from_storage_id)
    to_storage = storage_crud.get(db, transfer.to_storage_id)
    if from_storage and from_storage.club_id != item.club_id:
        raise HTTPException(status_code=400, detail="Source storage belongs to another club")
    if to_storage and to_storage.club_id != item.club_id:
        raise HTTPException(status_code=400, detail="Destination storage belongs to another club")

    try:
        return transfer_service.create_transfer(db, data=transfer)
    except BusinessRuleError as e:
        _handle_business_rule(e)


@router.get("/", response_model=List[TransferResponse])
def get_all_transfers(
    skip: int = 0,
    limit: int = 100,
    current_user: User | None = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """Get movement history of your clubs"""
    query = db.query(Transfer).join(Item, Item.id == Transfer.item_id)
    query = access_service.filter_by_clubs(query, Item.club_id, db, current_user)
    return query.order_by(Transfer.id.desc()).offset(skip).limit(limit).all()


@router.get("/{transfer_id}", response_model=TransferResponse)
def get_transfer(
    transfer_id: int,
    current_user: User | None = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """Get transfer by ID"""
    return _get_visible_transfer(db, current_user, transfer_id)


@router.get("/item/{item_id}", response_model=List[TransferResponse])
def get_transfers_by_item(
    item_id: int,
    current_user: User | None = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """Get movement history of an item"""
    item = item_crud.get(db, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    access_service.ensure_staff(db, current_user, item.club_id)
    return transfer_crud.get_by_item(db, item_id)


@router.get("/from/{storage_id}", response_model=List[TransferResponse])
def get_transfers_from_storage(
    storage_id: int,
    current_user: User | None = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """Get all transfers sent from a storage"""
    storage = storage_crud.get(db, storage_id)
    if not storage:
        raise HTTPException(status_code=404, detail="Storage not found")
    access_service.ensure_staff(db, current_user, storage.club_id)
    return transfer_crud.get_by_from_storage(db, storage_id)


@router.get("/to/{storage_id}", response_model=List[TransferResponse])
def get_transfers_to_storage(
    storage_id: int,
    current_user: User | None = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """Get all transfers received by a storage"""
    storage = storage_crud.get(db, storage_id)
    if not storage:
        raise HTTPException(status_code=404, detail="Storage not found")
    access_service.ensure_staff(db, current_user, storage.club_id)
    return transfer_crud.get_by_to_storage(db, storage_id)
