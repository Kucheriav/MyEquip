"""Club-level access control.

The source of truth for access is `club_members`: which clubs a user
belongs to and with what role. `users.role` is only a summary flag for
the GUI (a user may be a tourist in one club and a storekeeper in
another).

Roles:
- leader      - full control of the club (staff + management)
- storekeeper - operational staff: items, issue/return, repairs, transfers
- tourist     - club client, no admin access
"""
from typing import Iterable, Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.config import config
from app.models import ClubMember
from app.services.exceptions import BusinessRuleError

STAFF_ROLES = ("leader", "storekeeper")


def auth_disabled() -> bool:
    """Open development mode: access checks are skipped."""
    return not config.AUTH_ENABLED


def _ids(db: Session, user_id: int, roles: Optional[Iterable[str]] = None) -> set[int]:
    query = db.query(ClubMember.club_id).filter(ClubMember.user_id == user_id)
    if roles is not None:
        query = query.filter(ClubMember.role.in_(list(roles)))
    return {row[0] for row in query.all()}


def all_club_ids(db: Session, user) -> set[int]:
    """Clubs the user belongs to in any role (read access)."""
    if user is None:
        return set()
    return _ids(db, user.id)


def staff_club_ids(db: Session, user) -> set[int]:
    """Clubs where the user is leader or storekeeper."""
    if user is None:
        return set()
    return _ids(db, user.id, STAFF_ROLES)


def leader_club_ids(db: Session, user) -> set[int]:
    if user is None:
        return set()
    return _ids(db, user.id, ("leader",))


def filter_by_clubs(query, column, db: Session, user, staff: bool = True):
    """Restrict a query to the user's clubs.

    `column` is the model column holding the club id (for items and
    things linked to items the caller joins Item first and passes
    Item.club_id). In open development mode the query is returned
    unchanged.
    """
    if auth_disabled():
        return query
    club_ids = staff_club_ids(db, user) if staff else all_club_ids(db, user)
    return query.filter(column.in_(club_ids))


def member_role(db: Session, user_id: int, club_id: int) -> Optional[str]:
    member = (
        db.query(ClubMember)
        .filter(ClubMember.user_id == user_id, ClubMember.club_id == club_id)
        .first()
    )
    return member.role if member else None


def is_staff_of(db: Session, user, club_id: int) -> bool:
    if auth_disabled():
        return True
    if user is None:
        return False
    return member_role(db, user.id, club_id) in STAFF_ROLES


def is_leader_of(db: Session, user, club_id: int) -> bool:
    if auth_disabled():
        return True
    if user is None:
        return False
    return member_role(db, user.id, club_id) == "leader"


# ---------- guards (raise HTTP 403) ----------
def ensure_leader_any(user):
    """The user must have the leader role somewhere (for manager-only
    endpoints such as creating a club or an invite)."""
    if auth_disabled():
        return
    if user is None or user.role != "leader":
        raise HTTPException(status_code=403, detail="Only leaders can perform this action")


def ensure_staff(db: Session, user, club_id: int, what: str = "this action"):
    if is_staff_of(db, user, club_id):
        return
    raise HTTPException(
        status_code=403, detail=f"Access denied: you are not staff of this club ({what})"
    )


def ensure_leader(db: Session, user, club_id: int, what: str = "this action"):
    if is_leader_of(db, user, club_id):
        return
    raise HTTPException(
        status_code=403, detail=f"Access denied: only the club leader can do this ({what})"
    )


def ensure_club_visible(db: Session, user, club_id: int):
    if auth_disabled():
        return
    if user is None or member_role(db, user.id, club_id) is None:
        raise HTTPException(status_code=403, detail="Access denied: club is not yours")


# ---------- membership management ----------
def list_members(db: Session, club_id: int, role: Optional[str] = None):
    query = db.query(ClubMember).filter(ClubMember.club_id == club_id)
    if role:
        query = query.filter(ClubMember.role == role)
    return query.order_by(ClubMember.id).all()


def add_member(db: Session, user_id: int, club_id: int, role: str = "tourist") -> ClubMember:
    """Add a user to a club (or change the role of an existing member).
    A club can have only one leader (enforced here)."""
    if role not in ("leader", "storekeeper", "tourist"):
        raise BusinessRuleError(f"Unknown club role: {role}")

    existing = (
        db.query(ClubMember)
        .filter(ClubMember.user_id == user_id, ClubMember.club_id == club_id)
        .first()
    )
    if role == "leader":
        another = (
            db.query(ClubMember)
            .filter(
                ClubMember.club_id == club_id,
                ClubMember.role == "leader",
                ClubMember.user_id != user_id,
            )
            .first()
        )
        if another:
            raise BusinessRuleError("This club already has a leader")

    if existing:
        existing.role = role
        db.add(existing)
        db.commit()
        db.refresh(existing)
        member = existing
    else:
        member = ClubMember(user_id=user_id, club_id=club_id, role=role)
        db.add(member)
        db.commit()
        db.refresh(member)

    # Keep the summary role in sync (never downgrade a leader or a
    # storekeeper of another club).
    from app.models import User
    user = db.query(User).filter(User.id == user_id).first()
    if user is not None:
        if role == "leader":
            user.role = "leader"
        elif role == "storekeeper" and user.role == "tourist":
            user.role = "storekeeper"
        db.add(user)
        db.commit()

    return member


def remove_member(db: Session, user_id: int, club_id: int) -> bool:
    member = (
        db.query(ClubMember)
        .filter(ClubMember.user_id == user_id, ClubMember.club_id == club_id)
        .first()
    )
    if member is None:
        return False
    if member.role == "leader":
        raise BusinessRuleError("The club leader cannot be removed from the club")
    db.delete(member)
    db.commit()

    # Recalculate the summary role: leader > storekeeper > tourist.
    remaining = db.query(ClubMember).filter(ClubMember.user_id == user_id).all()
    roles = {m.role for m in remaining}
    from app.models import User
    user = db.query(User).filter(User.id == user_id).first()
    if user is not None:
        if "leader" in roles:
            user.role = "leader"
        elif "storekeeper" in roles:
            user.role = "storekeeper"
        else:
            user.role = "tourist"
        db.add(user)
        db.commit()
    return True
