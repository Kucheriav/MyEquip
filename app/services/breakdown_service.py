"""Domain services: keep Item.status in sync with Breakdown records.

Rule: a breakdown puts the item into 'maintenance'; once every breakdown
of the item is repaired, it goes back to 'available'.
"""
from sqlalchemy.orm import Session
from app.crud.breakdown_crud import breakdown_crud
from app.crud.item_crud import item_crud
from app.models import Breakdown
from app.schemas.breakdown_schema import BreakdownCreate, BreakdownUpdate
from app.services.exceptions import BusinessRuleError


def create_breakdown(db: Session, data: BreakdownCreate) -> Breakdown:
    """Log a breakdown and switch the item to 'maintenance'."""
    item = item_crud.get(db, data.item_id)
    if not item:
        raise BusinessRuleError("Item not found")

    breakdown = breakdown_crud.create(db, obj_in=data)

    item.status = "maintenance"
    db.add(item)
    db.commit()
    db.refresh(item)

    return breakdown


def update_breakdown(
    db: Session, breakdown_id: int, data: BreakdownUpdate
) -> Breakdown:
    """Generic update; if this closes the last unrepaired breakdown of the
    item, the item returns to 'available', otherwise stays in 'maintenance'."""
    breakdown = breakdown_crud.get(db, breakdown_id)
    if not breakdown:
        raise BusinessRuleError("Breakdown not found")

    updated = breakdown_crud.update(db, db_obj=breakdown, obj_in=data)
    _sync_item_status(db, updated)
    return updated


def repair_breakdown(
    db: Session,
    breakdown_id: int,
    repairer_id: int | None,
    repaired_date,
) -> Breakdown:
    """Mark a single breakdown as repaired."""
    breakdown = breakdown_crud.get(db, breakdown_id)
    if not breakdown:
        raise BusinessRuleError("Breakdown not found")
    if breakdown.repaired_date is not None:
        raise BusinessRuleError("Breakdown is already repaired")

    breakdown.repaired_date = repaired_date
    breakdown.repairer_id = repairer_id
    db.add(breakdown)
    db.commit()
    db.refresh(breakdown)

    _sync_item_status(db, breakdown)
    return breakdown


def _sync_item_status(db: Session, breakdown: Breakdown):
    """Set the item's status depending on whether open breakdowns remain."""
    item = item_crud.get(db, breakdown.item_id)
    if not item:
        return

    open_breakdowns = [
        b for b in breakdown_crud.get_by_item(db, item.id)
        if b.repaired_date is None
    ]
    item.status = "maintenance" if open_breakdowns else "available"
    db.add(item)
    db.commit()
    db.refresh(item)
