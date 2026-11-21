"""Web pages (Jinja2) on top of the existing API.

Every handler is a thin shell: fetch data through app.web.bff, render a
template, redirect after a successful POST (PRG). Business rules and
role checks stay inside /api, nothing is duplicated here.
"""
from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path
from typing import Optional
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app import labels
from app.web import auth, bff

router = APIRouter(include_in_schema=False)

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
}

ITEM_STATUSES = ("available", "issued", "maintenance", "lost")


# ---------- helpers ----------
def render(request: Request, name: str, user: Optional[dict] = None,
           status_code: int = 200, **context) -> HTMLResponse:
    context.setdefault("error", request.query_params.get("error"))
    context.setdefault("ok", FLASH_MESSAGES.get(request.query_params.get("ok", "")))
    context["request"] = request
    context["user"] = user
    context["csrf_token"] = auth.csrf_value(request)
    return templates.TemplateResponse(request, name, context, status_code=status_code)


def safe_next(target: Optional[str]) -> str:
    """Only same-site relative redirects are allowed after login."""
    if not target or not target.startswith("/") or target.startswith("//"):
        return "/app/items"
    return target


def with_query(path: str, **params) -> str:
    query = urlencode({key: value for key, value in params.items() if value not in (None, "")})
    return f"{path}?{query}" if query else path


def is_staff(user: dict) -> bool:
    """Leader or storekeeper of at least one club."""
    if user.get("role") in labels.STAFF_ROLES:
        return True
    return any(
        membership.get("role") in labels.STAFF_ROLES
        for membership in user.get("memberships") or []
    )


def fio(user: Optional[dict]) -> str:
    if not user:
        return ""
    return f"{user.get('surname', '')} {user.get('name', '')}".strip()


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


def club_storages(storages: list, club_id: Optional[int]) -> list:
    return [storage for storage in storages if storage.get("club_id") == club_id]


async def load_references(token: Optional[str]):
    _, clubs = await bff.get("/api/clubs/", token)
    _, storages = await bff.get("/api/storages/", token)
    _, categories = await bff.get("/api/categories/", token)
    return clubs or [], storages or [], categories or []


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


# ---------- authentication ----------
@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request, next: str = ""):
    if await auth.current_user(request):
        return RedirectResponse(safe_next(next), status_code=303)
    return render(request, "login.html", next=safe_next(next))


@router.post("/login")
async def login_submit(
    request: Request,
    login: str = Form(...),
    password: str = Form(...),
    next: str = Form("/app/items"),
):
    status, payload = await bff.post(
        "/api/auth/login", json={"login": login.strip(), "password": password})
    if status != 200 or not isinstance(payload, dict):
        return render(
            request, "login.html",
            error=bff.error_detail(payload, "Неверный телефон/почта или пароль"),
            login=login, next=safe_next(next), status_code=401)
    response = RedirectResponse(safe_next(next), status_code=303)
    auth.start_session(response, payload["access_token"])
    return response


@router.post("/logout")
async def logout(request: Request):
    response = RedirectResponse("/login?ok=logged_out", status_code=303)
    auth.end_session(response)
    return response


@router.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    if await auth.current_user(request):
        return RedirectResponse("/app/items", status_code=303)
    return render(request, "register.html")


@router.post("/register")
async def register_submit(
    request: Request,
    invite_code: str = Form(...),
    name: str = Form(...),
    surname: str = Form(...),
    phone: str = Form(...),
    password: str = Form(...),
    email: str = Form(""),
    date_of_birth: str = Form(""),
):
    payload = {
        "invite_code": invite_code.strip().upper(),
        "name": name.strip(),
        "surname": surname.strip(),
        "phone": phone.strip(),
        "password": password,
    }
    if email.strip():
        payload["email"] = email.strip()
    if date_of_birth.strip():
        payload["date_of_birth"] = date_of_birth.strip()

    status, data = await bff.post("/api/auth/register", json=payload)
    if status != 201:
        return render(
            request, "register.html", status_code=400,
            error=bff.error_detail(data, "Не удалось зарегистрироваться"),
            form={"invite_code": invite_code, "name": name, "surname": surname,
                  "phone": phone, "email": email})
    return RedirectResponse("/login?ok=registered", status_code=303)


# ---------- app ----------
@router.get("/app")
async def app_index():
    return RedirectResponse("/app/items", status_code=303)


@router.get("/app/items", response_class=HTMLResponse)
async def items_page(
    request: Request,
    user: dict = Depends(auth.require_user),
    club_id: Optional[int] = None,
    storage_id: Optional[int] = None,
    status: Optional[str] = None,
):
    if not is_staff(user):
        return render(request, "tourist.html", user=user)

    token = auth.session_token(request)
    clubs, storages, categories = await load_references(token)
    code, items = await bff.get(
        "/api/items/", token, club_id=club_id, storage_id=storage_id, status=status)
    items = items if isinstance(items, list) else []

    club_names = {club["id"]: club["name"] for club in clubs}
    storage_names = {storage["id"]: storage["name"] for storage in storages}
    category_names = {category["id"]: category.get("title", "") for category in categories}

    return render(
        request, "items.html", user=user, active="items",
        items=items, clubs=clubs, storages=storages, statuses=ITEM_STATUSES,
        club_names=club_names, storage_names=storage_names,
        category_names=category_names,
        filters={"club_id": club_id, "storage_id": storage_id, "status": status},
        api_error=bff.error_detail(items) if code >= 400 else None,
    )


@router.get("/app/distributions", response_class=HTMLResponse)
async def distributions_page(
    request: Request,
    user: dict = Depends(auth.require_user),
    item_id: Optional[int] = None,
):
    if not is_staff(user):
        return render(request, "tourist.html", user=user)

    token = auth.session_token(request)
    clubs, storages, _ = await load_references(token)
    _, items = await bff.get("/api/items/", token)
    _, users = await bff.get("/api/users/", token)
    _, distributions = await bff.get("/api/distributions/", token)

    items = items if isinstance(items, list) else []
    users = users if isinstance(users, list) else []
    distributions = distributions if isinstance(distributions, list) else []

    items_by_id = {item["id"]: item for item in items}
    storage_names = {storage["id"]: storage["name"] for storage in storages}
    user_names = {entry["id"]: fio(entry) for entry in users}

    available_items = [item for item in items if item.get("status") == "available"]
    selected_item = items_by_id.get(item_id) if item_id else None
    if selected_item is None and available_items:
        selected_item = available_items[0]
    selected_club_id = selected_item.get("club_id") if selected_item else None
    getters = club_members(users, selected_club_id)

    rows = []
    for record in sorted(distributions, key=lambda row: row["id"], reverse=True):
        item = items_by_id.get(record["item_id"], {})
        rows.append({
            **record,
            "item_name": item.get("name", ""),
            "item_club_id": item.get("club_id"),
            "item_storage_id": item.get("storage_id"),
            "storage_name": storage_names.get(item.get("storage_id"), ""),
            "giver_name": user_names.get(record.get("giver_id"), ""),
            "getter_name": user_names.get(record.get("getter_id"), ""),
            "accepter_name": user_names.get(record.get("accepter_id"), ""),
            "accept_storages": club_storages(storages, item.get("club_id")),
        })

    return render(
        request, "distributions.html", user=user, active="distributions",
        available_items=available_items, selected_item=selected_item,
        selected_club_id=selected_club_id, getters=getters,
        storage_names=storage_names, rows=rows,
        today=date.today().isoformat(),
        default_expiration=(date.today() + timedelta(days=14)).isoformat(),
        me_id=user["id"],
    )


@router.get("/app/distributions/getters", response_class=HTMLResponse)
async def getters_fragment(
    request: Request,
    item_id: Optional[int] = None,
    user: dict = Depends(auth.require_user),
):
    """HTMX fragment: members of the selected item's club."""
    token = auth.session_token(request)
    _, items = await bff.get("/api/items/", token)
    _, users = await bff.get("/api/users/", token)

    items_by_id = {item["id"]: item for item in (items or [])}
    selected = items_by_id.get(item_id)
    club_id = selected.get("club_id") if selected else None
    getters = club_members(users or [], club_id)

    return templates.TemplateResponse(
        request, "_getter_select.html", {"getters": getters})


@router.post("/app/distributions")
async def issue_item(
    request: Request,
    item_id: int = Form(...),
    getter_id: int = Form(...),
    expiration_date: str = Form(""),
    comment: str = Form(""),
    csrf_token: str = Form(""),
    user: dict = Depends(auth.require_user),
):
    if not auth.check_csrf(request, csrf_token):
        return csrf_error()
    if not is_staff(user):
        return RedirectResponse("/app/distributions?error=Недостаточно прав", status_code=303)

    payload = {
        "item_id": item_id,
        "giver_id": user["id"],
        "getter_id": getter_id,
        "date": date.today().isoformat(),
        "status": "issued",
    }
    expiration = parse_date(expiration_date, date.today() + timedelta(days=14))
    if expiration_date.strip():
        payload["expiration_date"] = expiration
    if comment.strip():
        payload["comment"] = comment.strip()

    status, data = await bff.post("/api/distributions/", auth.session_token(request), payload)
    if status != 201:
        return RedirectResponse(
            with_query("/app/distributions", item_id=item_id,
                       error=bff.error_detail(data)),
            status_code=303)
    return RedirectResponse("/app/distributions?ok=issued", status_code=303)


@router.post("/app/distributions/{distribution_id}/accept")
async def accept_item(
    request: Request,
    distribution_id: int,
    storage_id: Optional[int] = Form(None),
    accepting_date: str = Form(""),
    comment: str = Form(""),
    csrf_token: str = Form(""),
    user: dict = Depends(auth.require_user),
):
    if not auth.check_csrf(request, csrf_token):
        return csrf_error()
    if not is_staff(user):
        return RedirectResponse("/app/distributions?error=Недостаточно прав", status_code=303)

    payload = {
        "accepter_id": user["id"],
        "accepting_date": parse_date(accepting_date, date.today()),
    }
    if storage_id:
        payload["storage_id"] = storage_id
    if comment.strip():
        payload["comment"] = comment.strip()

    status, data = await bff.post(
        f"/api/distributions/{distribution_id}/return",
        auth.session_token(request), payload)
    if status != 200:
        return RedirectResponse(
            with_query("/app/distributions", error=bff.error_detail(data)),
            status_code=303)
    return RedirectResponse("/app/distributions?ok=accepted", status_code=303)
