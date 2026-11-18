from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.crud import UserCRUD
from app.schemas.user_schema import UserCreate, UserUpdate, UserResponse
from app.dependencies import require_auth
from app.models import User, ClubMember
from app.services import access_service

router = APIRouter(prefix="/api/users", tags=["users"], dependencies=[Depends(require_auth)])
user_crud = UserCRUD()


def _shared_club_ids(db: Session, current_user: User, user: User) -> set[int]:
    return {m.club_id for m in user.memberships}


def _get_visible_user(db: Session, current_user: User | None, user_id: int) -> User:
    """A user is visible if they share at least one staff club with me."""
    user = user_crud.get(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if access_service.auth_disabled() or current_user is None:
        return user
    if not (access_service.staff_club_ids(db, current_user) & _shared_club_ids(db, current_user, user)):
        raise HTTPException(status_code=403, detail="Access denied: user is not in your clubs")
    return user


def _ensure_leader_of_user(db: Session, current_user: User | None, user: User):
    """Only a leader of a club shared with the user may edit/delete them."""
    if access_service.auth_disabled() or current_user is None:
        return
    shared = access_service.leader_club_ids(db, current_user) & _shared_club_ids(db, current_user, user)
    if not shared:
        raise HTTPException(status_code=403, detail="Access denied: only the club leader can do this")


@router.post("/", response_model=UserResponse, status_code=201)
def create_user(
    user: UserCreate,
    current_user: User | None = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """Record a tourist in one of the leader's clubs (leaders only)."""
    access_service.ensure_leader_any(current_user)
    if user.club_id is None:
        raise HTTPException(status_code=400, detail="club_id is required: a tourist belongs to a club")
    access_service.ensure_leader(db, current_user, user.club_id)

    # Email is optional: only check for duplicates when one is given
    if user.email:
        db_user = user_crud.get_by_email(db, email=user.email)
        if db_user:
            raise HTTPException(status_code=400, detail="Email already registered")
    # Phone is unique in the DB; answer with a readable error instead of
    # a 500 IntegrityError
    if user_crud.get_by_phone(db, phone=user.phone):
        raise HTTPException(status_code=400, detail="This phone number is already registered")

    payload = user.model_dump(exclude={"club_id"})
    db_user = User(**payload)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)

    access_service.add_member(db, db_user.id, user.club_id, "tourist")
    return db_user


@router.get("/{user_id}", response_model=UserResponse)
def get_user(
    user_id: int,
    current_user: User | None = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """Get user by ID (only users of your clubs)"""
    return _get_visible_user(db, current_user, user_id)


@router.get("/", response_model=List[UserResponse])
def get_all_users(
    skip: int = 0,
    limit: int = 100,
    club_id: int | None = None,
    current_user: User | None = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """Get users of your clubs (leaders and storekeepers, read-only)."""
    if access_service.auth_disabled():
        return user_crud.get_all(db, skip=skip, limit=limit)

    club_ids = access_service.staff_club_ids(db, current_user)
    if club_id is not None:
        if club_id not in club_ids and current_user is not None and current_user.role == "leader":
            raise HTTPException(status_code=403, detail="Access denied: club is not yours")
        club_ids = club_ids & {club_id}
    if not club_ids:
        return []

    return (
        db.query(User)
        .join(ClubMember, ClubMember.user_id == User.id)
        .filter(ClubMember.club_id.in_(club_ids))
        .distinct()
        .offset(skip)
        .limit(limit)
        .all()
    )


@router.put("/{user_id}", response_model=UserResponse)
def update_user(
    user_id: int,
    user_update: UserUpdate,
    current_user: User | None = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """Update user (leader of a shared club only)"""
    db_user = _get_visible_user(db, current_user, user_id)
    _ensure_leader_of_user(db, current_user, db_user)

    if user_update.email:
        other = user_crud.get_by_email(db, email=user_update.email)
        if other and other.id != user_id:
            raise HTTPException(status_code=400, detail="Email already registered")
    if user_update.phone:
        other = user_crud.get_by_phone(db, phone=user_update.phone)
        if other and other.id != user_id:
            raise HTTPException(status_code=400, detail="This phone number is already registered")

    return user_crud.update(db, db_obj=db_user, obj_in=user_update)


@router.delete("/{user_id}", status_code=204)
def delete_user(
    user_id: int,
    current_user: User | None = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """Delete user (leader of a shared club only)"""
    db_user = _get_visible_user(db, current_user, user_id)
    _ensure_leader_of_user(db, current_user, db_user)
    if not user_crud.delete(db, user_id):
        raise HTTPException(status_code=404, detail="User not found")
    return None
