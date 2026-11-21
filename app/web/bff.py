"""Thin server-side HTTP client used by the web pages.

The pages never touch CRUD or services directly: they call the same
/api endpoints the PyQt GUI uses. That keeps every access check in one
place (a storekeeper cannot do more through the browser than through the
desktop client) and means the API contract has a single implementation.

Requests go through httpx's ASGI transport, so there is no extra network
hop: the call is dispatched inside the running app.
"""
from __future__ import annotations

from typing import Any, Optional

import httpx

_app = None
_client: Optional[httpx.AsyncClient] = None


def _asgi_app():
    """The FastAPI app, imported lazily.

    app.main imports the web router, so importing app.main at module level
    here would be circular. By the time the first request is served the
    module is fully loaded.
    """
    global _app
    if _app is None:
        from app.main import app as fastapi_app

        _app = fastapi_app
    return _app


def http() -> httpx.AsyncClient:
    global _client
    if _client is None:
        _client = httpx.AsyncClient(
            transport=httpx.ASGITransport(app=_asgi_app()),
            base_url="http://myequip.local",
            timeout=30.0,
        )
    return _client


def headers(token: Optional[str]) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"} if token else {}


def _json(response: httpx.Response) -> Any:
    try:
        return response.json()
    except ValueError:
        return None


async def get(path: str, token: Optional[str] = None, **params) -> tuple[int, Any]:
    query = {key: value for key, value in params.items() if value not in (None, "")}
    response = await http().get(path, headers=headers(token), params=query or None)
    return response.status_code, _json(response)


async def post(path: str, token: Optional[str] = None, json: Any = None) -> tuple[int, Any]:
    response = await http().post(path, headers=headers(token), json=json)
    return response.status_code, _json(response)


# The API speaks English; the web UI speaks Russian. Only the messages a
# user can realistically see are translated, everything else falls back.
MESSAGES = {
    "Invalid invite code": "Неверный код приглашения",
    "Invite code is already used": "Этот код приглашения уже использован",
    "This account is already registered, please log in":
        "Этот аккаунт уже зарегистрирован — войдите по паролю",
    "Incorrect login or password": "Неверный телефон/почта или пароль",
    "Not authenticated": "Нужно войти в систему",
    "Access denied: user is not in your clubs": "Нет доступа к этому человеку",
    "Access denied: only the club leader can do this":
        "Это может сделать только руководитель клуба",
    "Access denied: club is not yours": "Этот клуб вам не принадлежит",
    "Only leaders can perform this action": "Это может сделать только руководитель",
    "Item is not available for issue": "Вещь недоступна для выдачи",
    "Distribution is already returned": "Эта выдача уже принята",
    "The getter is not a member of this club": "Получатель не состоит в клубе вещи",
    "The giver must be a leader or storekeeper of this club":
        "Выдающий должен быть руководителем или завхозом клуба",
    "The accepter must be a leader or storekeeper of this club":
        "Принимающий должен быть руководителем или завхозом клуба",
}


def error_detail(payload: Any, fallback: str = "Не удалось выполнить операцию") -> str:
    """Extract a readable message from an API error payload."""
    if isinstance(payload, dict):
        detail = payload.get("detail")
        if isinstance(detail, str):
            return MESSAGES.get(detail, detail)
        if isinstance(detail, list) and detail:
            first = detail[0]
            if isinstance(first, dict):
                return str(first.get("msg") or fallback)
    return fallback
