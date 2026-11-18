"""Authentication service: password hashing, JWT tokens, registration.

Registration flow (invite-code based):
- a valid unused invite code is required;
- the invite type decides the role: an independent leader (no clubs) or
  a storekeeper of the invite's club;
- if the phone (or email) matches an existing user without a real
  password (a tourist recorded by a leader), that user's account is
  upgraded in place (same id -> all history is preserved);
- otherwise a new user is created;
- the invite code is marked as used.

Login works by phone or email (login field containing '@' is treated
as an email). Legacy users created by the GUI with client-side sha256
hashes are still accepted.
"""
from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
import jwt
from sqlalchemy.orm import Session

from app.config import config
from app.crud.user_crud import user_crud
from app.models import User
from app.services import access_service, invite_service
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


def register_user(
    db: Session,
    name: str,
    surname: str,
    phone: str,
    password: str,
    invite_code: str,
    last_name: Optional[str] = None,
    email: Optional[str] = None,
    date_of_birth=None,
) -> User:
    """Register (or upgrade) a user according to the invite type."""
    invite = invite_service.validate_code(db, invite_code)

    # Match an existing tourist record by phone or (if no phone match) email
    existing = user_crud.get_by_phone(db, phone=phone)
    if existing is None and email:
        existing = user_crud.get_by_email(db, email=email)

    if existing is not None:
        # Only accounts with a real (bcrypt) password are protected;
        # leader-created records (no password or legacy client-side sha256)
        # are upgraded in place: same id, same history.
        if existing.pswd_hash and existing.pswd_hash.startswith("$2"):
            raise AuthError("This account is already registered, please log in")
        existing.name = name
        existing.surname = surname
        if last_name is not None:
            existing.last_name = last_name
        if email is not None:
            existing.email = email
        if date_of_birth is not None:
            existing.date_of_birth = date_of_birth
        if not existing.phone:
            existing.phone = phone
        existing.pswd_hash = hash_password(password)
        existing.status = "full"
        db.add(existing)
        db.commit()
        db.refresh(existing)
        user = existing
    else:
        user = User(
            name=name, surname=surname, last_name=last_name,
            date_of_birth=date_of_birth, email=email, phone=phone,
            pswd_hash=hash_password(password), status="full",
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    # Apply the role carried by the invite
    if invite.role == "storekeeper":
        if invite.club_id is None:
            raise AuthError("This invite is not linked to a club")
        if user.role != "leader":  # never downgrade a leader
            user.role = "storekeeper"
        user.status = "full"
        db.add(user)
        db.commit()
        db.refresh(user)
        access_service.add_member(db, user.id, invite.club_id, "storekeeper")
    else:
        user.role = "leader"
        user.status = "full"
        db.add(user)
        db.commit()
        db.refresh(user)

    invite_service.mark_used(db, invite, user.id)
    return user


def authenticate(db: Session, login: str, password: str) -> User:
    """Login by phone or email ('@' means email)."""
    if "@" in login:
        user = user_crud.get_by_email(db, email=login)
    else:
        user = user_crud.get_by_phone(db, phone=login)
    if not user or not verify_password(password, user.pswd_hash):
        raise AuthError("Incorrect login or password")
    return user


def get_current_user(db: Session, token: str) -> User:
    user = user_crud.get(db, decode_token(token))
    if not user:
        raise AuthError("User not found")
    return user
