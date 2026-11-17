from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from datetime import datetime
from typing import List
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user_optional
from app.models import InviteCode, User
from app.services import invite_service

router = APIRouter(prefix="/api/invites", tags=["invites"])


class InviteResponse(BaseModel):
    id: int
    code: str
    created_by: int | None
    created_at: datetime
    used_by: int | None
    used_at: datetime | None

    class Config:
        from_attributes = True


def _require_leader(current_user: User | None) -> User:
    if current_user is None or current_user.status != "full":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only validated leaders can manage invite codes",
        )
    return current_user


@router.post("/", response_model=InviteResponse, status_code=201)
def create_invite(
    current_user: User | None = Depends(get_current_user_optional),
    db: Session = Depends(get_db),
):
    """Generate a new one-time invite code (leaders only)"""
    leader = _require_leader(current_user)
    return invite_service.generate_code(db, created_by=leader.id)


@router.get("/", response_model=List[InviteResponse])
def list_invites(
    current_user: User | None = Depends(get_current_user_optional),
    db: Session = Depends(get_db),
):
    """List all invite codes with usage status (leaders only)"""
    _require_leader(current_user)
    return invite_service.list_codes(db)
