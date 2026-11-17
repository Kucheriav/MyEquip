"""Invite codes: the only way to self-register as a leader ('full').

The very first code is generated automatically at server startup when the
database is empty and written to invite_code.txt in the project root.
Existing leaders can generate further codes via the API.
"""
import secrets
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models import InviteCode
from app.services.exceptions import AuthError


def generate_code(db: Session, created_by: int | None = None) -> InviteCode:
    """Generate a unique one-time invite code."""
    while True:
        code = secrets.token_hex(4).upper()  # e.g. 'A1B2C3D4'
        if not db.query(InviteCode).filter(InviteCode.code == code).first():
            break

    invite = InviteCode(
        code=code,
        created_by=created_by,
        created_at=datetime.now(timezone.utc),
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


def list_codes(db: Session) -> list[InviteCode]:
    return db.query(InviteCode).order_by(InviteCode.id).all()
