from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.crud import ClubCRUD, UserCRUD
from app.schemas.club_schema import ClubCreate, ClubUpdate, ClubResponse
from app.schemas.club_member_schema import ClubMemberCreate, ClubMemberResponse
from app.dependencies import require_auth
from app.models import User
from app.services import access_service
from app.services.exceptions import BusinessRuleError

router = APIRouter(prefix="/api/clubs", tags=["clubs"], dependencies=[Depends(require_auth)])
club_crud = ClubCRUD()
user_crud = UserCRUD()


@router.post("/", response_model=ClubResponse, status_code=201)
def create_club(
    club: ClubCreate,
    current_user: User | None = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """Create a new club; the creator becomes its leader."""
    access_service.ensure_leader_any(current_user)

    db_club = club_crud.get_by_name(db, name=club.name)
    if db_club:
        raise HTTPException(status_code=400, detail="Club already exists")

    db_club = club_crud.create(db, obj_in=club)
    if current_user is not None:
        access_service.add_member(db, current_user.id, db_club.id, "leader")
    return db_club


@router.get("/{club_id}/members", response_model=List[ClubMemberResponse])
def get_club_members(
    club_id: int,
    current_user: User | None = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """List club members (leaders only)"""
    access_service.ensure_leader(db, current_user, club_id)
    return access_service.list_members(db, club_id)


@router.post("/{club_id}/members", response_model=ClubMemberResponse, status_code=201)
def add_club_member(
    club_id: int,
    request: ClubMemberCreate,
    current_user: User | None = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """Add an existing user to the club as storekeeper or tourist
    (leaders only). This is also how a storekeeper gets extra clubs."""
    access_service.ensure_leader(db, current_user, club_id)
    if request.role not in ("storekeeper", "tourist"):
        raise HTTPException(status_code=400, detail="Role must be 'storekeeper' or 'tourist'")
    if user_crud.get(db, request.user_id) is None:
        raise HTTPException(status_code=404, detail="User not found")
    try:
        return access_service.add_member(db, request.user_id, club_id, request.role)
    except BusinessRuleError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{club_id}/members/{user_id}", status_code=204)
def remove_club_member(
    club_id: int,
    user_id: int,
    current_user: User | None = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """Remove a member from the club (leaders only; the leader cannot be removed)"""
    access_service.ensure_leader(db, current_user, club_id)
    try:
        if not access_service.remove_member(db, user_id, club_id):
            raise HTTPException(status_code=404, detail="Member not found")
    except BusinessRuleError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return None


@router.get("/{club_id}", response_model=ClubResponse)
def get_club(
    club_id: int,
    current_user: User | None = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """Get club by ID"""
    club = club_crud.get(db, club_id)
    if not club:
        raise HTTPException(status_code=404, detail="Club not found")
    access_service.ensure_club_visible(db, current_user, club_id)
    return club


@router.get("/", response_model=List[ClubResponse])
def get_all_clubs(
    skip: int = 0,
    limit: int = 100,
    current_user: User | None = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """Get the clubs the current user belongs to"""
    if access_service.auth_disabled():
        return club_crud.get_all(db, skip=skip, limit=limit)
    if current_user is None:
        return []
    return club_crud.get_by_member(db, current_user.id)[skip:skip + limit]


@router.put("/{club_id}", response_model=ClubResponse)
def update_club(
    club_id: int,
    club_update: ClubUpdate,
    current_user: User | None = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """Update club (leader only)"""
    db_club = club_crud.get(db, club_id)
    if not db_club:
        raise HTTPException(status_code=404, detail="Club not found")
    access_service.ensure_leader(db, current_user, club_id)
    if club_update.name is not None:
        other = club_crud.get_by_name(db, name=club_update.name)
        if other and other.id != club_id:
            raise HTTPException(status_code=400, detail="Club already exists")
    return club_crud.update(db, db_obj=db_club, obj_in=club_update)


@router.delete("/{club_id}", status_code=204)
def delete_club(
    club_id: int,
    current_user: User | None = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """Delete club (leader only)"""
    if not club_crud.get(db, club_id):
        raise HTTPException(status_code=404, detail="Club not found")
    access_service.ensure_leader(db, current_user, club_id)
    if not club_crud.delete(db, club_id):
        raise HTTPException(status_code=404, detail="Club not found")
    return None
