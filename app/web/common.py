"""Shared pieces for the web pages: templates, rendering, small helpers."""
from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Optional
from urllib.parse import urlencode

from fastapi import Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app import labels
from app.web import auth, bff

templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))
templates.env.globals.update(
    translate_status=labels.translate_status,
    translate_role=labels.translate_role,
    staff_roles=labels.STAFF_ROLES,
)

FLASH_MESSAGES = {
    "issued": "Снаряжение выдано",
    "accepted": "Снаряжение принято",
    "registered": "Регистрация завершена — войдите с новым паролем",
    "logged_out": "Вы вышли из системы",
    "transferred": "Снаряжение перемещено",
    "breakdown_reported": "Поломка зарегистрирована",
    "breakdown_repaired": "Поломка отмечена как отремонтированная",
    "person_created": "Человек добавлен в клуб",
    "person_updated": "Данные человека сохранены",
    "person_deleted": "Человек удалён",
    "club_created": "Клуб создан",
    "club_updated": "Название клуба изменено",
    "member_added": "Роль в клубе сохранена",
    "member_removed": "Человек убран из клуба",
    "invite_created": "Код приглашения создан",
    "storage_created": "Склад добавлен",
    "storage_updated": "Склад сохранён",
    "storage_deleted": "Склад удалён",
    "category_created": "Категория добавлена",
    "category_updated": "Категория сохранена",
    "parameter_attached": "Свойство добавлено к категории",
    "parameter_detached": "Свойство отвязано от категории",
    "item_created": "Снаряжение добавлено",
    "item_updated": "Снаряжение сохранено",
    "item_deleted": "Снаряжение удалено",
}

ITEM_STATUSES = ("available", "issued", "maintenance", "lost")

USER_STATUSES = (("guest", "Гость"), ("unverified", "Не подтверждён"), ("full", "Подтверждён"))

PARAM_TYPES = (("int", "Число"), ("float", "Число дробное"), ("str", "Текст"), ("bool", "Да/Нет"))
PARAM_TYPE_LABELS = dict(PARAM_TYPES)


def render(request: Request, name: str, user: Optional[dict] = None,
           status_code: int = 200, **context) -> HTMLResponse:
    context.setdefault("error", request.query_params.get("error"))
    context.setdefault("ok", FLASH_MESSAGES.get(request.query_params.get("ok", "")))
    context["request"] = request
    context["user"] = user
    context["csrf_token"] = auth.csrf_value(request)
    context["is_leader"] = bool(user) and user.get("role") == "leader"
    context["staff"] = bool(user) and is_staff(user)
    context["led_clubs"] = led_clubs(user)
    return templates.TemplateResponse(request, name, context, status_code=status_code)


def fragment(request: Request, name: str, **context) -> HTMLResponse:
    """HTMX partial: only the fragment body, no layout."""
    context["request"] = request
    return templates.TemplateResponse(request, name, context)


def safe_next(target: Optional[str]) -> str:
    """Only same-site relative redirects are allowed after login."""
    if not target or not target.startswith("/") or target.startswith("//"):
        return "/app/items"
    return target


def with_query(path: str, **params) -> str:
    query = urlencode({key: value for key, value in params.items() if value not in (None, "")})
    return f"{path}?{query}" if query else path


def redirect(path: str, **params):
    from fastapi.responses import RedirectResponse

    return RedirectResponse(with_query(path, **params), status_code=303)


def is_staff(user: dict) -> bool:
    """Leader or storekeeper of at least one club."""
    if user.get("role") in labels.STAFF_ROLES:
        return True
    return any(
        membership.get("role") in labels.STAFF_ROLES
        for membership in user.get("memberships") or []
    )


def is_leader(user: dict) -> bool:
    return user.get("role") == "leader"


def led_clubs(user: Optional[dict]) -> list:
    """Clubs the user leads (the only ones where the leader-only API works)."""
    if not user:
        return []
    return [
        membership.get("club_id")
        for membership in user.get("memberships") or []
        if membership.get("role") == "leader"
    ]


def fio(user: Optional[dict]) -> str:
    if not user:
        return ""
    parts = [user.get("surname", ""), user.get("name", ""), user.get("last_name") or ""]
    return " ".join(part for part in parts if part).strip()


def club_members(users: list, club_id: Optional[int]) -> list:
    """People who belong to the club (any role)."""
    if club_id is None:
        return []
    result = []
    for user in users:
        for membership in user.get("memberships") or []:
            if membership.get("club_id") == club_id:
                result.append(user)
                break
    return result


def club_staff(users: list, club_id: Optional[int]) -> list:
    """People with a staff role in the club."""
    return [
        user for user in club_members(users, club_id)
        if any(
            membership.get("club_id") == club_id
            and membership.get("role") in labels.STAFF_ROLES
            for membership in user.get("memberships") or []
        )
    ]


def club_storages(storages: list, club_id: Optional[int]) -> list:
    return [storage for storage in storages if storage.get("club_id") == club_id]


def parse_date(value: Optional[str], fallback: date) -> str:
    try:
        return date.fromisoformat((value or "").strip()).isoformat()
    except ValueError:
        return fallback.isoformat()


def csrf_error() -> HTMLResponse:
    return HTMLResponse(
        "<h1>400</h1><p>Форма устарела или запрос пришёл не с этого сайта. "
        "Обновите страницу и повторите.</p>",
        status_code=400,
    )


async def load_references(token: Optional[str]):
    _, clubs = await bff.get("/api/clubs/", token)
    _, storages = await bff.get("/api/storages/", token)
    _, categories = await bff.get("/api/categories/", token)
    return clubs or [], storages or [], categories or []


def names_by_id(rows: list, field: str = "name") -> dict:
    return {row["id"]: row.get(field, "") for row in rows}
