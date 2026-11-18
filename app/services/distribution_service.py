"""Domain services: keep Item.status in sync with Distribution records.

Rule: an Item status is derived from the last event applied to it
(issue -> 'issued', return -> 'available', lost -> 'lost').
"""
from sqlalchemy.orm import Session
from app.crud.distribution_crud import distribution_crud
from app.crud.item_crud import item_crud
from app.crud.storage_crud import storage_crud
from app.models import Distribution, Transfer
from app.schemas.distribution_schema import DistributionCreate, DistributionUpdate
from app.services.exceptions import BusinessRuleError


# What an item's status becomes after a distribution changes to this status
ITEM_STATUS_BY_DISTRIBUTION_STATUS = {
    "issued": "issued",
    "extended": "issued",
    "returned": "available",
    "lost": "lost",
}


def create_distribution(db: Session, data: DistributionCreate) -> Distribution:
    """Issue an item: validate it is available, log the distribution,
    switch the item to 'issued'."""
    item = item_crud.get(db, data.item_id)
    if not item:
        raise BusinessRuleError("Item not found")
    if item.status != "available":
        raise BusinessRuleError(
            f"Item is not available for issue (current status: {item.status})"
        )

    distribution = distribution_crud.create(db, obj_in=data)

    item.status = "issued"
    db.add(item)
    db.commit()
    db.refresh(item)

    return distribution


def update_distribution(
    db: Session, distribution_id: int, data: DistributionUpdate
) -> Distribution:
    """Generic update; if the status changes, sync the item status too."""
    distribution = distribution_crud.get(db, distribution_id)
    if not distribution:
        raise BusinessRuleError("Distribution not found")

    new_status = data.status
    if new_status and new_status not in ITEM_STATUS_BY_DISTRIBUTION_STATUS:
        raise BusinessRuleError(f"Unknown distribution status: {new_status}")

    old_status = distribution.status
    updated = distribution_crud.update(db, db_obj=distribution, obj_in=data)

    if new_status and new_status != old_status:
        item = item_crud.get(db, updated.item_id)
        if item:
            item.status = ITEM_STATUS_BY_DISTRIBUTION_STATUS[new_status]
            db.add(item)
            db.commit()
            db.refresh(item)

    return updated


def return_distribution(
    db: Session,
    distribution_id: int,
    accepter_id: int | None,
    accepting_date,
    comment: str | None = None,
    storage_id: int | None = None,
) -> Distribution:
    """Accept an item back.

    The item becomes 'available' and is put back into a storage. By
    default that is its current storage; the accepter may choose
    another storage of the same club, in which case a Transfer record
    keeps the movement history (mover = giver, receiver = accepter).

    Everything is written in one transaction, so a failed return never
    leaves a half-updated item behind.
    """
    distribution = distribution_crud.get(db, distribution_id)
    if not distribution:
        raise BusinessRuleError("Distribution not found")
    if distribution.status == "returned":
        raise BusinessRuleError("Distribution is already returned")

    item = item_crud.get(db, distribution.item_id)
    if not item:
        raise BusinessRuleError("Item not found")

    from_storage_id = item.storage_id
    target_storage_id = storage_id if storage_id is not None else from_storage_id

    transfer = None
    if target_storage_id != from_storage_id:
        storage = storage_crud.get(db, target_storage_id)
        if not storage:
            raise BusinessRuleError("Destination storage not found")
        if storage.club_id != item.club_id:
            raise BusinessRuleError("Destination storage belongs to another club")
        # The item is still 'issued' while being accepted, so the usual
        # transfer_service checks do not apply here.
        transfer = Transfer(
            item_id=item.id,
            from_storage_id=from_storage_id,
            to_storage_id=target_storage_id,
            date=accepting_date,
            mover_id=distribution.giver_id,
            receiver_id=accepter_id,
            comment=comment or "Принято при возврате снаряжения",
        )

    distribution.status = "returned"
    distribution.accepter_id = accepter_id
    distribution.accepting_date = accepting_date
    if comment is not None:
        distribution.comment = comment

    item.storage_id = target_storage_id
    if item.status == "issued":
        item.status = "available"

    db.add(distribution)
    db.add(item)
    if transfer is not None:
        db.add(transfer)
    db.commit()
    db.refresh(distribution)

    return distribution
