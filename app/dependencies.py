"""Shared FastAPI dependencies."""
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.config import config
from app.database import get_db
from app.services import auth_service, AuthError

bearer_scheme = HTTPBearer(auto_error=False)


def require_auth(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
):
    """Auth dependency. While config.AUTH_ENABLED is False it is a no-op
    (open mode for local GUI development); when enabled, a valid
    Bearer token is required on every endpoint of routers using it."""
    if not config.AUTH_ENABLED:
        return None

    if credentials is None:
        raise HTTPException(status_code=401, detail="Not authenticated",
                            headers={"WWW-Authenticate": "Bearer"})
    try:
        user = auth_service.get_current_user(db, credentials.credentials)
    except AuthError as e:
        raise HTTPException(status_code=401, detail=str(e),
                            headers={"WWW-Authenticate": "Bearer"})
    # Gives the access log a useful user= field for API requests too.
    request.state.user_id = getattr(user, "id", "-")
    return user


def get_current_user_optional(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
):
    """Returns the current user if a valid token is provided, otherwise None."""
    if credentials is None:
        return None
    try:
        user = auth_service.get_current_user(db, credentials.credentials)
    except AuthError:
        return None
    request.state.user_id = getattr(user, "id", "-")
    return user
