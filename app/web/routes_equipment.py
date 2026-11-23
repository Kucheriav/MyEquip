"""Equipment: list, issue and acceptance."""
from __future__ import annotations

from datetime import date, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, Form, Request

from app import labels
from app.web import auth, bff
from app.web.common import (
    ITEM_STATUSES, club_members, club_storages, csrf_error, fio, is_staff,
    page_request, pager, render, redirect, with_query,
)

router = APIRouter(include_in_schema=False)


def _staff_clubs(user: dict, clubs: list) -> list:
    allowed = {
        membership.get("club_id")
        for membership in user.get("memberships") or []
        if membership.get("role") in labels.STAFF_ROLES
    }
    return [club for club in clubs if club["id"] in allowed]


async def _parameters_with_values(token: str, category_id: Optional[int]) -> list:
    """Effective parameters of a category with their predefined values."""
    if not category_id:
        return []
    _, parameters = await bff.get(
        f"/api/categories/{category_id}/parameters", token)
    _, values = await bff.get("/api/values/", token)

    values_by_parameter: dict[int, list] = {}
    for value in values or []:
        values_by_parameter.setdefault(value["parameter_id"], []).append(value)

    return [
        {**parameter, "variants": values_by_parameter.get(parameter["id"], [])}
        for parameter in parameters or []
    ]


async def _parameter_payloads(request: Request, token: str,
                              category_id: int) -> list:
    """Read the dynamic property inputs from the submitted form."""
    form = await request.form()
    payloads = []
    for parameter in await _parameters_with_values(token, category_id):
        parameter_id = parameter["id"]
        if parameter["variants"]:
            raw = form.get(f"value_{parameter_id}")
            if raw not in (None, ""):
                payloads.append({
                    "parameter_id": parameter_id, "value_id": int(raw)})
        else:
            raw = (form.get(f"custom_{parameter_id}") or "").strip()
            if raw:
                payloads.append({
                    "parameter_id": parameter_id, "custom_value": raw})
    return payloads


@router.get("/app")
async def app_index():
    return redirect("/app/items")


@router.get("/app/items")
async def items_page(
    request: Request,
    user: dict = Depends(auth.require_user),
    club_id: Optional[int] = None,
    storage_id: Optional[int] = None,
    status: Optional[str] = None,
    q: Optional[str] = None,
):
    if not is_staff(user):
        return render(request, "tourist.html", user=user)

    token = auth.session_token(request)
    page, skip, limit = page_request(request)
    _, clubs = await bff.get("/api/clubs/", token)
    _, storages = await bff.get("/api/storages/", token)
    _, categories = await bff.get("/api/categories/", token)
    _, item_parameters = await bff.get("/api/item-parameters/", token, limit=1000)
    _, parameters = await bff.get("/api/parameters/", token)
    _, values = await bff.get("/api/values/", token)
    code, items = await bff.get(
        "/api/items/", token, club_id=club_id, storage_id=storage_id, status=status,
        q=q, skip=skip, limit=limit)
    items = items if isinstance(items, list) else []

    parameter_names = {p["id"]: p["name"] for p in parameters or []}
    value_texts = {v["id"]: v["value"] for v in values or []}
    props_by_item: dict[int, list] = {}
    for entry in item_parameters or []:
        if entry.get("value_id") is not None:
            text = value_texts.get(entry["value_id"], "")
        else:
            text = entry.get("custom_value") or ""
        if text == "true":
            text = "да"
        elif text == "false":
            text = "нет"
        name = parameter_names.get(entry["parameter_id"], "")
        props_by_item.setdefault(entry["item_id"], []).append(f"{name} — {text}")

    pager_data = pager(
        items, page, "/app/items",
        q=q, club_id=club_id, storage_id=storage_id, status=status,
    )

    return render(
        request, "items.html", user=user, active="items",
        items=pager_data["rows"], pager=pager_data,
        clubs=clubs or [], storages=storages or [], statuses=ITEM_STATUSES,
        club_names={c["id"]: c["name"] for c in clubs or []},
        storage_names={s["id"]: s["name"] for s in storages or []},
        category_names={c["id"]: c.get("title", "") for c in categories or []},
        props_by_item=props_by_item,
        filters={"club_id": club_id, "storage_id": storage_id, "status": status},
        q=q or "",
        api_error=bff.error_detail(items) if code >= 400 else None,
    )


@router.get("/app/distributions")
async def distributions_page(
    request: Request,
    user: dict = Depends(auth.require_user),
    item_id: Optional[int] = None,
):
    if not is_staff(user):
        return render(request, "tourist.html", user=user)

    token = auth.session_token(request)
    page, skip, limit = page_request(request)
    _, clubs = await bff.get("/api/clubs/", token)
    _, storages = await bff.get("/api/storages/", token)
    _, items = await bff.get("/api/items/", token)
    _, users = await bff.get("/api/users/", token)
    _, distributions = await bff.get(
        "/api/distributions/", token, skip=skip, limit=limit)

    storages = storages or []
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

    pager_data = pager(distributions, page, "/app/distributions")
    rows = []
    for record in pager_data["rows"]:
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
        storage_names=storage_names, rows=rows, pager=pager_data,
        today=date.today().isoformat(),
        default_expiration=(date.today() + timedelta(days=14)).isoformat(),
        me_id=user["id"],
    )


@router.get("/app/distributions/getters")
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

    return render(request, "_getter_select.html", getters=getters)


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
        return redirect("/app/distributions", error="Недостаточно прав")

    payload = {
        "item_id": item_id,
        "giver_id": user["id"],
        "getter_id": getter_id,
        "date": date.today().isoformat(),
        "status": "issued",
    }
    if expiration_date.strip():
        from app.web.common import parse_date

        payload["expiration_date"] = parse_date(expiration_date, date.today())
    if comment.strip():
        payload["comment"] = comment.strip()

    status, data = await bff.post("/api/distributions/", auth.session_token(request), payload)
    if status != 201:
        return redirect("/app/distributions", item_id=item_id,
                        error=bff.error_detail(data))
    return redirect("/app/distributions", ok="issued")


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
        return redirect("/app/distributions", error="Недостаточно прав")

    from app.web.common import parse_date

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
        return redirect("/app/distributions", error=bff.error_detail(data))
    return redirect("/app/distributions", ok="accepted")


# ---------- item create / edit ----------
def _item_context(user: dict, clubs: list, storages: list, categories: list,
                  club_id: Optional[int] = None,
                  selected_category_id: Optional[int] = None,
                  selected_storage_id: Optional[int] = None) -> dict:
    """Filter the lookups to one club and pick sensible defaults."""
    staff_clubs = _staff_clubs(user, clubs)
    if club_id is None:
        club_id = staff_clubs[0]["id"] if staff_clubs else None

    club_storages_list = club_storages(storages, club_id)
    club_categories = [c for c in categories if c.get("club_id") == club_id]

    category_ids = {c["id"] for c in club_categories}
    storage_ids = {s["id"] for s in club_storages_list}
    if selected_category_id not in category_ids:
        selected_category_id = club_categories[0]["id"] if club_categories else None
    if selected_storage_id not in storage_ids:
        selected_storage_id = club_storages_list[0]["id"] if club_storages_list else None

    return {
        "clubs": staff_clubs,
        "club_id": club_id,
        "storages": club_storages_list,
        "categories": club_categories,
        "selected_category_id": selected_category_id,
        "selected_storage_id": selected_storage_id,
        "selected_storage_name": next(
            (storage["name"] for storage in club_storages_list
             if storage["id"] == selected_storage_id),
            "",
        ),
    }


@router.get("/app/items/new")
async def new_item_page(
    request: Request,
    user: dict = Depends(auth.require_user),
    club_id: Optional[int] = None,
    category_id: Optional[int] = None,
):
    if not is_staff(user):
        return render(request, "tourist.html", user=user)

    token = auth.session_token(request)
    _, clubs = await bff.get("/api/clubs/", token)
    _, storages = await bff.get("/api/storages/", token)
    _, categories = await bff.get("/api/categories/", token)

    context = _item_context(
        user, clubs or [], storages or [], categories or [], club_id=club_id,
        selected_category_id=category_id)
    parameters = await _parameters_with_values(
        token, context["selected_category_id"])

    return render(
        request, "item_form.html", user=user, active="items", mode="create",
        action="/app/items", item=None, parameters=parameters,
        current_values={}, statuses=ITEM_STATUSES, **context,
    )


@router.get("/app/items/options")
async def item_options_fragment(
    request: Request,
    club_id: Optional[int] = None,
    user: dict = Depends(auth.require_user),
):
    """HTMX fragment: categories and storages of the chosen club."""
    token = auth.session_token(request)
    _, clubs = await bff.get("/api/clubs/", token)
    _, storages = await bff.get("/api/storages/", token)
    _, categories = await bff.get("/api/categories/", token)

    context = _item_context(
        user, clubs or [], storages or [], categories or [], club_id=club_id)
    parameters = await _parameters_with_values(
        token, context["selected_category_id"])

    return render(
        request, "_item_options.html", parameters=parameters,
        current_values={}, **context,
    )


@router.get("/app/items/fields")
async def item_fields_fragment(
    request: Request,
    category_id: Optional[int] = None,
    user: dict = Depends(auth.require_user),
):
    """HTMX fragment: property inputs of the chosen category."""
    parameters = await _parameters_with_values(
        auth.session_token(request), category_id)
    return render(
        request, "_item_param_fields.html", parameters=parameters,
        current_values={},
    )


@router.get("/app/items/{item_id}/edit")
async def edit_item_page(
    request: Request,
    item_id: int,
    user: dict = Depends(auth.require_user),
):
    if not is_staff(user):
        return render(request, "tourist.html", user=user)

    token = auth.session_token(request)
    code, item = await bff.get(f"/api/items/{item_id}", token)
    if code != 200 or not isinstance(item, dict):
        return redirect("/app/items", error=bff.error_detail(item, "Вещь не найдена"))

    _, clubs = await bff.get("/api/clubs/", token)
    _, storages = await bff.get("/api/storages/", token)
    _, categories = await bff.get("/api/categories/", token)
    _, item_parameters = await bff.get(
        f"/api/item-parameters/item/{item_id}", token)

    context = _item_context(
        user, clubs or [], storages or [], categories or [],
        club_id=item["club_id"],
        selected_category_id=item["category_id"],
        selected_storage_id=item["storage_id"],
    )
    parameters = await _parameters_with_values(token, item["category_id"])

    current_values = {}
    for entry in item_parameters or []:
        current_values[entry["parameter_id"]] = {
            "value_id": entry.get("value_id"),
            "custom_value": entry.get("custom_value") or "",
        }

    return render(
        request, "item_form.html", user=user, active="items", mode="edit",
        action=f"/app/items/{item_id}", item=item, parameters=parameters,
        current_values=current_values, statuses=ITEM_STATUSES,
        club_name=next(
            (club["name"] for club in clubs or [] if club["id"] == item["club_id"]),
            "",
        ),
        **context,
    )


@router.post("/app/items")
async def create_item(
    request: Request,
    name: str = Form(...),
    category_id: int = Form(...),
    storage_id: int = Form(...),
    status: str = Form("available"),
    serial_number: str = Form(""),
    csrf_token: str = Form(""),
    user: dict = Depends(auth.require_user),
):
    if not auth.check_csrf(request, csrf_token):
        return csrf_error()
    if not is_staff(user):
        return redirect("/app/items", error="Недостаточно прав")

    payload = {"name": name.strip(), "category_id": category_id,
               "storage_id": storage_id, "status": status}
    if serial_number.strip():
        payload["serial_number"] = serial_number.strip()

    token = auth.session_token(request)
    status_code, data = await bff.post("/api/items/", token, payload)
    if status_code != 201:
        return redirect("/app/items/new", error=bff.error_detail(data))

    item_id = data.get("id")
    for extra in await _parameter_payloads(request, token, category_id):
        await bff.post("/api/item-parameters/", token, {"item_id": item_id, **extra})

    return redirect("/app/items", ok="item_created")


@router.post("/app/items/{item_id}")
async def update_item(
    request: Request,
    item_id: int,
    name: str = Form(...),
    category_id: int = Form(...),
    status: str = Form("available"),
    serial_number: str = Form(""),
    csrf_token: str = Form(""),
    user: dict = Depends(auth.require_user),
):
    if not auth.check_csrf(request, csrf_token):
        return csrf_error()
    if not is_staff(user):
        return redirect("/app/items", error="Недостаточно прав")

    token = auth.session_token(request)
    payload = {
        "name": name.strip(),
        "category_id": category_id,
        "status": status,
        "serial_number": serial_number.strip() or None,
    }
    status_code, data = await bff.put(
        f"/api/items/{item_id}", token, payload)
    if status_code != 200:
        return redirect(f"/app/items/{item_id}/edit",
                        error=bff.error_detail(data))

    # Properties are replaced as a set: the API has no per-value update.
    _, existing = await bff.get(
        f"/api/item-parameters/item/{item_id}", token)
    for entry in existing or []:
        await bff.delete(f"/api/item-parameters/{entry['id']}", token)
    for extra in await _parameter_payloads(request, token, category_id):
        await bff.post("/api/item-parameters/", token, {"item_id": item_id, **extra})

    return redirect("/app/items", ok="item_updated")
