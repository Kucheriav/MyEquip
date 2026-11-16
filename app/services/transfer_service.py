"""Domain service: moving items between storages.

Rule: a transfer is only possible from the item's current storage,
the item must not be currently issued or lost, and after the transfer
the item physically lives in the destination storage.
"""
from sqlalchemy.orm import Session
from app.crud.item_crud import item_crud
from app.crud.storage_crud import storage_crud
from app.crud.transfer_crud import transfer_crud
from app.models import Transfer
from app.schemas.transfer_schema import TransferCreate
from app.services.exceptions import BusinessRuleError


def create_transfer(db: Session, data: TransferCreate) -> Transfer:
    item = item_crud.get(db, data.item_id)
    if not item:
        raise BusinessRuleError("Item not found")

    if data.from_storage_id == data.to_storage_id:
        raise BusinessRuleError("Source and destination storages must differ")

    if storage_crud.get(db, data.from_storage_id) is None:
        raise BusinessRuleError("Source storage not found")
    if storage_crud.get(db, data.to_storage_id) is None:
        raise BusinessRuleError("Destination storage not found")

    if item.status == "issued":
        raise BusinessRuleError("Item is currently issued to a person and cannot be transferred")
    if item.status == "lost":
        raise BusinessRuleError("Item is lost and cannot be transferred")

    if item.storage_id != data.from_storage_id:
        raise BusinessRuleError(
            f"Item is not in the source storage "
            f"(actual storage id: {item.storage_id})"
        )

    transfer = transfer_crud.create(db, obj_in=data)

    item.storage_id = data.to_storage_id
    db.add(item)
    db.commit()
    db.refresh(item)

    return transfer
