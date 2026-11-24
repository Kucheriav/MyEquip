"""Catalog: storages, categories and their properties."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Form, Request

from app.web import auth, bff
from app.web.common import (
    PARAM_TYPES, PARAM_TYPE_LABELS, csrf_error, is_staff, led_clubs, render,
    redirect,
)

router = APIRouter(include_in_schema=False)


def _led_club_list(user: dict, clubs: list) -> list:
    led_ids = set(led_clubs(user))
    return [club for club in clubs if club["id"] in led_ids]


# ---------- storages ----------
@router.get("/app/storages")
async def storages_page(
    request: Request,
    user: dict = Depends(auth.require_user),
):
    if not is_staff(user):
        return render(request, "tourist.html", user=user)

    token = auth.session_token(request)
    code, storages = await bff.get("/api/storages/", token)
    _, clubs = await bff.get("/api/clubs/", token)

    storages = storages if isinstance(storages, list) else []
    clubs = clubs if isinstance(clubs, list) else []
    club_names = {club["id"]: club["name"] for club in clubs}
    led_ids = set(led_clubs(user))

    rows = [
        {**storage, "club_name": club_names.get(storage["club_id"], "")}
        for storage in storages
    ]

    return render(
        request, "storages.html", user=user, active="storages",
        rows=rows, clubs=_led_club_list(user, clubs), led_ids=led_ids,
        api_error=bff.error_detail(storages) if code >= 400 else None,
    )


@router.post("/app/storages")
async def create_storage(
    request: Request,
    club_id: int = Form(...),
    name: str = Form(...),
    address: str = Form(""),
    csrf_token: str = Form(""),
    user: dict = Depends(auth.require_user),
):
    if not auth.check_csrf(request, csrf_token):
        return csrf_error(request)
    if not is_staff(user):
        return redirect("/app/storages", error="Недостаточно прав")

    if not name.strip():
        return redirect("/app/storages", error="Укажите название склада")

    payload = {"name": name.strip(), "club_id": club_id}
    if address.strip():
        payload["address"] = address.strip()

    status, data = await bff.post(
        "/api/storages/", auth.session_token(request), payload)
    if status != 201:
        return redirect("/app/storages", error=bff.error_detail(data))
    return redirect("/app/storages", ok="storage_created")


# ---------- categories ----------
async def _category_parameters(token: str, category_id: int) -> list:
    """Effective parameters with their predefined values grouped in."""
    _, parameters = await bff.get(
        f"/api/categories/{category_id}/parameters", token)
    _, values = await bff.get("/api/values/", token)

    values_by_parameter: dict[int, list] = {}
    for value in values or []:
        values_by_parameter.setdefault(value["parameter_id"], []).append(value)

    result = []
    for parameter in parameters or []:
        result.append({
            **parameter,
            "variants": values_by_parameter.get(parameter["id"], []),
            "type_label": PARAM_TYPE_LABELS.get(parameter.get("param_type"),
                                                parameter.get("param_type", "")),
        })
    return result


@router.get("/app/categories")
async def categories_page(
    request: Request,
    user: dict = Depends(auth.require_user),
    category_id: Optional[int] = None,
):
    if not is_staff(user):
        return render(request, "tourist.html", user=user)

    token = auth.session_token(request)
    _, clubs = await bff.get("/api/clubs/", token)
    code, categories = await bff.get("/api/categories/", token)

    clubs = clubs if isinstance(clubs, list) else []
    categories = categories if isinstance(categories, list) else []
    club_names = {club["id"]: club["name"] for club in clubs}
    titles = {category["id"]: category.get("title", "") for category in categories}

    selected = category_id
    if selected not in titles:
        selected = categories[0]["id"] if categories else None
    parameters = await _category_parameters(token, selected) if selected else []

    rows = [
        {
            **category,
            "club_name": club_names.get(category["club_id"], ""),
            "parent_title": titles.get(category.get("parent_id"), "") or "—",
        }
        for category in categories
    ]

    return render(
        request, "categories.html", user=user, active="categories",
        rows=rows, categories=categories, clubs=_led_club_list(user, clubs),
        club_names=club_names, led_ids=set(led_clubs(user)),
        selected_category_id=selected, selected_title=titles.get(selected, ""),
        parameters=parameters, param_types=PARAM_TYPES,
        api_error=bff.error_detail(categories) if code >= 400 else None,
    )


@router.post("/app/categories")
async def create_category(
    request: Request,
    club_id: int = Form(...),
    title: str = Form(...),
    parent_id: Optional[int] = Form(None),
    csrf_token: str = Form(""),
    user: dict = Depends(auth.require_user),
):
    if not auth.check_csrf(request, csrf_token):
        return csrf_error(request)
    if not is_staff(user):
        return redirect("/app/categories", error="Недостаточно прав")

    if not title.strip():
        return redirect("/app/categories", error="Укажите название категории")

    payload = {"title": title.strip(), "club_id": club_id}
    if parent_id:
        payload["parent_id"] = parent_id

    status, data = await bff.post(
        "/api/categories/", auth.session_token(request), payload)
    if status != 201:
        return redirect("/app/categories", error=bff.error_detail(data))
    return redirect("/app/categories", category_id=data.get("id"),
                    ok="category_created")


@router.post("/app/categories/{category_id}/parameters")
async def attach_parameter(
    request: Request,
    category_id: int,
    name: str = Form(...),
    param_type: str = Form("str"),
    variants: str = Form(""),
    csrf_token: str = Form(""),
    user: dict = Depends(auth.require_user),
):
    if not auth.check_csrf(request, csrf_token):
        return csrf_error(request)
    if not is_staff(user):
        return redirect("/app/categories", category_id=category_id,
                        error="Недостаточно прав")

    token = auth.session_token(request)
    if not name.strip():
        return redirect("/app/categories", category_id=category_id,
                        error="Введите название свойства")
    if param_type not in dict(PARAM_TYPES):
        return redirect("/app/categories", category_id=category_id,
                        error="Неизвестный тип свойства")

    # Reuse a parameter with the same name; create it (with its variants)
    # only when it does not exist yet - same rule as the desktop client.
    _, parameters = await bff.get("/api/parameters/", token)
    existing = next(
        (p for p in parameters or [] if p["name"].lower() == name.strip().lower()),
        None,
    )

    if existing is None:
        status, data = await bff.post(
            "/api/parameters/", token,
            {"name": name.strip(), "param_type": param_type})
        if status != 201:
            return redirect("/app/categories", category_id=category_id,
                            error=bff.error_detail(data))
        existing = data
        for variant in [v.strip() for v in variants.split(",") if v.strip()]:
            await bff.post("/api/values/", token,
                           {"value": variant, "parameter_id": existing["id"]})

    status, data = await bff.post(
        f"/api/categories/{category_id}/parameters", token,
        {"parameter_id": existing["id"]})
    if status not in (200, 201):
        return redirect("/app/categories", category_id=category_id,
                        error=bff.error_detail(data))
    return redirect("/app/categories", category_id=category_id,
                    ok="parameter_attached")


@router.post("/app/categories/{category_id}/parameters/{parameter_id}/detach")
async def detach_parameter(
    request: Request,
    category_id: int,
    parameter_id: int,
    csrf_token: str = Form(""),
    user: dict = Depends(auth.require_user),
):
    if not auth.check_csrf(request, csrf_token):
        return csrf_error(request)
    if not is_staff(user):
        return redirect("/app/categories", category_id=category_id,
                        error="Недостаточно прав")

    status, data = await bff.delete(
        f"/api/categories/{category_id}/parameters/{parameter_id}",
        auth.session_token(request))
    if status != 204:
        return redirect("/app/categories", category_id=category_id,
                        error=bff.error_detail(data))
    return redirect("/app/categories", category_id=category_id,
                    ok="parameter_detached")
