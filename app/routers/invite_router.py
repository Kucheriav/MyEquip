from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from datetime import datetime
from typing import List, Optional
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import require_auth
from app.models import InviteCode, User
from app.services import access_service, invite_service
from app.services.exceptions import BusinessRuleError

router = APIRouter(prefix="/api/invites", tags=["invites"])


class InviteResponse(BaseModel):
    id: int
    code: str
    role: str
    club_id: Optional[int] = None
    created_by: Optional[int] = None
    created_at: datetime
    used_by: Optional[int] = None
    used_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class InviteCreateRequest(BaseModel):
    role: str = "leader"  # 'leader' (independent) or 'storekeeper' (club staff)
    club_id: Optional[int] = None  # required for a storekeeper invite


@router.post("/", response_model=InviteResponse, status_code=201)
def create_invite(
    request: InviteCreateRequest,
    current_user: Optional[User] = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """Generate a new one-time invite code (leaders only).

    A leader invite creates an independent leader with no clubs; a
    storekeeper invite is bound to one of the leader's own clubs."""
    access_service.ensure_leader_any(current_user)

    if request.role not in invite_service.INVITE_ROLES:
        raise HTTPException(status_code=400, detail=f"Unknown invite role: {request.role}")

    if request.role == "storekeeper":
        if request.club_id is None:
            raise HTTPException(status_code=400, detail="A storekeeper invite needs club_id")
        access_service.ensure_leader(db, current_user, request.club_id)
    elif request.club_id is not None:
        raise HTTPException(status_code=400, detail="A leader invite must not have club_id")

    try:
        return invite_service.generate_code(
            db,
            created_by=current_user.id if current_user else None,
            role=request.role,
            club_id=request.club_id,
        )
    except BusinessRuleError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/", response_model=List[InviteResponse])
def list_invites(
    current_user: Optional[User] = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """List the invite codes this leader has created (leaders only)"""
    access_service.ensure_leader_any(current_user)
    return invite_service.list_codes(
        db, created_by=current_user.id if current_user else None
    )
