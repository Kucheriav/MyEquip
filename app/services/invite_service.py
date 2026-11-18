"""Invite codes: the only way to self-register.

The very first code is generated automatically at server startup when the
database is empty and written to invite_code.txt in the project root.

Two kinds of invites:
- 'leader'      - an independent leader (starts without clubs);
- 'storekeeper' - staff of the club referenced by club_id.

Existing leaders can generate further codes via the API.
"""
import secrets
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models import InviteCode
from app.services.exceptions import AuthError, BusinessRuleError

INVITE_ROLES = ("leader", "storekeeper")


def generate_code(
    db: Session,
    created_by: int | None = None,
    role: str = "leader",
    club_id: int | None = None,
) -> InviteCode:
    """Generate a unique one-time invite code."""
    if role not in INVITE_ROLES:
        raise BusinessRuleError(f"Unknown invite role: {role}")
    if role == "storekeeper" and club_id is None:
        raise BusinessRuleError("A storekeeper invite must be linked to a club")
    if role == "leader":
        club_id = None

    while True:
        code = secrets.token_hex(4).upper()  # e.g. 'A1B2C3D4'
        if not db.query(InviteCode).filter(InviteCode.code == code).first():
            break

    invite = InviteCode(
        code=code,
        created_by=created_by,
        created_at=datetime.now(timezone.utc),
        role=role,
        club_id=club_id,
    )
    db.add(invite)
    db.commit()
    db.refresh(invite)
    return invite


def validate_code(db: Session, code: str) -> InviteCode:
    """Return the invite code record if it exists and is unused."""
    invite = db.query(InviteCode).filter(InviteCode.code == code.strip().upper()).first()
    if not invite:
        raise AuthError("Invalid invite code")
    if invite.used_by is not None:
        raise AuthError("Invite code is already used")
    return invite


def mark_used(db: Session, invite: InviteCode, user_id: int):
    """Mark a code as used (one-time use)."""
    invite.used_by = user_id
    invite.used_at = datetime.now(timezone.utc)
    db.add(invite)
    db.commit()


def list_codes(db: Session, created_by: int | None = None) -> list[InviteCode]:
    """List codes; with created_by only that leader's own codes."""
    query = db.query(InviteCode)
    if created_by is not None:
        query = query.filter(InviteCode.created_by == created_by)
    return query.order_by(InviteCode.id).all()
