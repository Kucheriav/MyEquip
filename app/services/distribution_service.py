"""Domain services: keep Item.status in sync with Distribution records.

Rule: an Item status is derived from the last event applied to it
(issue -> 'issued', return -> 'available', lost -> 'lost').
"""
from sqlalchemy.orm import Session
from app.crud.distribution_crud import distribution_crud
from app.crud.item_crud import item_crud
from app.models import Distribution
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
) -> Distribution:
    """Accept an item back: mark the distribution 'returned' and the
    item 'available'."""
    distribution = distribution_crud.get(db, distribution_id)
    if not distribution:
        raise BusinessRuleError("Distribution not found")
    if distribution.status == "returned":
        raise BusinessRuleError("Distribution is already returned")

    distribution.status = "returned"
    distribution.accepter_id = accepter_id
    distribution.accepting_date = accepting_date
    if comment is not None:
        distribution.comment = comment
    db.add(distribution)
    db.commit()
    db.refresh(distribution)

    item = item_crud.get(db, distribution.item_id)
    if item and item.status == "issued":
        item.status = "available"
        db.add(item)
        db.commit()
        db.refresh(item)

    return distribution
