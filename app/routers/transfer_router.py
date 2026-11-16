from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.crud.transfer_crud import transfer_crud
from app.schemas.transfer_schema import TransferCreate, TransferResponse
from app.services import transfer_service, BusinessRuleError
from app.dependencies import require_auth
from typing import List

router = APIRouter(prefix="/api/transfers", tags=["transfers"], dependencies=[Depends(require_auth)])


def _handle_business_rule(e: BusinessRuleError):
    message = str(e)
    status = 404 if "not found" in message.lower() else 400
    raise HTTPException(status_code=status, detail=message)


@router.post("/", response_model=TransferResponse, status_code=201)
def create_transfer(transfer: TransferCreate, db: Session = Depends(get_db)):
    """Move an item between storages (updates the item's storage and keeps history)"""
    try:
        return transfer_service.create_transfer(db, data=transfer)
    except BusinessRuleError as e:
        _handle_business_rule(e)


@router.get("/", response_model=List[TransferResponse])
def get_all_transfers(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """Get all transfers (movement history)"""
    return transfer_crud.get_all(db, skip=skip, limit=limit)


@router.get("/{transfer_id}", response_model=TransferResponse)
def get_transfer(transfer_id: int, db: Session = Depends(get_db)):
    """Get transfer by ID"""
    transfer = transfer_crud.get(db, transfer_id)
    if not transfer:
        raise HTTPException(status_code=404, detail="Transfer not found")
    return transfer


@router.get("/item/{item_id}", response_model=List[TransferResponse])
def get_transfers_by_item(item_id: int, db: Session = Depends(get_db)):
    """Get movement history of an item"""
    return transfer_crud.get_by_item(db, item_id)


@router.get("/from/{storage_id}", response_model=List[TransferResponse])
def get_transfers_from_storage(storage_id: int, db: Session = Depends(get_db)):
    """Get all transfers sent from a storage"""
    return transfer_crud.get_by_from_storage(db, storage_id)


@router.get("/to/{storage_id}", response_model=List[TransferResponse])
def get_transfers_to_storage(storage_id: int, db: Session = Depends(get_db)):
    """Get all transfers received by a storage"""
    return transfer_crud.get_by_to_storage(db, storage_id)
