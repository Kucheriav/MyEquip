from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from datetime import date
from typing import Optional
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.user_schema import UserResponse
from app.services import auth_service, AuthError
from app.dependencies import get_current_user_optional
from app.models import User

router = APIRouter(prefix="/api/auth", tags=["auth"])


class RegisterRequest(BaseModel):
    name: str
    surname: str
    last_name: Optional[str] = None
    date_of_birth: Optional[date] = None
    phone: str
    email: Optional[EmailStr] = None
    password: str
    invite_code: str


class LoginRequest(BaseModel):
    login: str  # phone or email
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


@router.post("/register", response_model=UserResponse, status_code=201)
def register(request: RegisterRequest, db: Session = Depends(get_db)):
    """Register as a leader using an invite code.

    If the phone matches an existing tourist record (created by a leader),
    the account is upgraded in place and all history is preserved."""
    try:
        return auth_service.register_user(
            db,
            name=request.name, surname=request.surname,
            phone=request.phone, password=request.password,
            invite_code=request.invite_code,
            last_name=request.last_name, email=request.email,
            date_of_birth=request.date_of_birth,
        )
    except AuthError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/login", response_model=TokenResponse)
def login(request: LoginRequest, db: Session = Depends(get_db)):
    """Authenticate (by phone or email) and get a JWT token"""
    try:
        user = auth_service.authenticate(db, login=request.login, password=request.password)
    except AuthError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))
    return TokenResponse(access_token=auth_service.create_access_token(user))


@router.get("/me", response_model=UserResponse)
def me(current_user: User | None = Depends(get_current_user_optional)):
    """Return the authenticated user (401 if no valid token)"""
    if current_user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    return current_user
