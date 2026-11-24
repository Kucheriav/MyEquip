"""Cookie session helpers for the web UI.

The JWT lives in an HttpOnly cookie, so page JavaScript can never read
it. A second cookie carries a CSRF token that every form must echo back
(on top of SameSite=Lax); without it a cross-site form post is rejected.
"""
from __future__ import annotations

import secrets
from typing import Optional
from urllib.parse import quote

from fastapi import Request
from fastapi.responses import RedirectResponse

from app.config import config
from app.web import bff

SESSION_COOKIE = "myequip_session"
CSRF_COOKIE = "myequip_csrf"
INVITE_FLASH_COOKIE = "myequip_new_invite"


class WebAuthRequired(Exception):
    """Raised for pages that need a logged-in user.

    app.main registers an exception handler that turns this into a
    redirect to /login (the API keeps returning plain 401 JSON).
    """


def login_redirect(request: Request) -> RedirectResponse:
    target = request.url.path
    if request.url.query:
        target += "?" + request.url.query
    return RedirectResponse(url=f"/login?next={quote(target)}", status_code=303)


async def current_user(request: Request) -> Optional[dict]:
    token = session_token(request)
    if not token:
        return None
    status, payload = await bff.get("/api/auth/me", token)
    if status != 200 or not isinstance(payload, dict):
        return None
    return payload


async def require_user(request: Request) -> dict:
    user = await current_user(request)
    if user is None:
        raise WebAuthRequired()
    request.state.user_id = user.get("id", "-")
    return user


def session_token(request: Request) -> Optional[str]:
    return request.cookies.get(SESSION_COOKIE)


def csrf_value(request: Request) -> str:
    return request.cookies.get(CSRF_COOKIE) or ""


def check_csrf(request: Request, submitted: Optional[str]) -> bool:
    expected = csrf_value(request)
    if not expected or not submitted:
        return False
    return secrets.compare_digest(expected, submitted)


def start_session(response, token: str) -> None:
    secure = config.WEB_COOKIE_SECURE
    max_age = config.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    response.set_cookie(
        SESSION_COOKIE, token, max_age=max_age, path="/",
        httponly=True, samesite="lax", secure=secure,
    )
    response.set_cookie(
        CSRF_COOKIE, secrets.token_urlsafe(32), max_age=max_age, path="/",
        httponly=True, samesite="lax", secure=secure,
    )


def end_session(response) -> None:
    response.delete_cookie(SESSION_COOKIE, path="/")
    response.delete_cookie(CSRF_COOKIE, path="/")


def set_invite_flash(response, code: str) -> None:
    """Hand a freshly generated invite code to the next page load.

    The code travels in a short-lived HttpOnly cookie instead of the URL,
    so it does not end up in browser history or access logs.
    """
    response.set_cookie(
        INVITE_FLASH_COOKIE, code, max_age=300, path="/",
        httponly=True, samesite="lax", secure=config.WEB_COOKIE_SECURE,
    )


def clear_invite_flash(response) -> None:
    response.delete_cookie(INVITE_FLASH_COOKIE, path="/")
