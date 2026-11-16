"""Authentication service: password hashing, JWT tokens, current user.

Passwords are hashed server-side with bcrypt. For users created by the
legacy GUI flow (client-side sha256 stored directly in pswd_hash) the
verification falls back to sha256 comparison.
"""
from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
import jwt
from sqlalchemy.orm import Session

from app.config import config
from app.crud.user_crud import user_crud
from app.models import User
from app.schemas.user_schema import UserCreate
from app.services.exceptions import AuthError

ALGORITHM = "HS256"


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, stored_hash: Optional[str]) -> bool:
    if not stored_hash:
        return False
    if stored_hash.startswith("$2"):  # bcrypt hash
        try:
            return bcrypt.checkpw(password.encode("utf-8"), stored_hash.encode("utf-8"))
        except ValueError:
            return False
    # Legacy: GUI-computed sha256 hexdigest
    import hashlib
    return hashlib.sha256(password.encode("utf-8")).hexdigest() == stored_hash


def create_access_token(user: User) -> str:
    expires = datetime.now(timezone.utc) + timedelta(minutes=config.ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {"sub": str(user.id), "exp": expires}
    return jwt.encode(payload, config.SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> int:
    """Returns the user id encoded in the token."""
    try:
        payload = jwt.decode(token, config.SECRET_KEY, algorithms=[ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise AuthError("Token expired")
    except jwt.InvalidTokenError:
        raise AuthError("Invalid token")
    user_id = payload.get("sub")
    if user_id is None:
        raise AuthError("Invalid token payload")
    return int(user_id)


def register_user(db: Session, email: str, password: str,
                  name: str, surname: str,
                  last_name: Optional[str] = None,
                  phone: Optional[str] = None,
                  date_of_birth=None) -> User:
    """Create a user with a server-side bcrypt hash."""
    if user_crud.get_by_email(db, email=email):
        raise AuthError("Email already registered")

    create_data = UserCreate(
        name=name, surname=surname, last_name=last_name,
        email=email, phone=phone or "",
        pswd_hash=hash_password(password), status="full",
        date_of_birth=date_of_birth,
    )
    return user_crud.create(db, obj_in=create_data)


def authenticate(db: Session, email: str, password: str) -> User:
    user = user_crud.get_by_email(db, email=email)
    if not user or not verify_password(password, user.pswd_hash):
        raise AuthError("Incorrect email or password")
    return user


def get_current_user(db: Session, token: str) -> User:
    user = user_crud.get(db, decode_token(token))
    if not user:
        raise AuthError("User not found")
    return user
