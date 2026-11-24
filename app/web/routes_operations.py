"""Operations: moving equipment between storages and reporting breakdowns."""
from __future__ import annotations

from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Form, Request

from app.web import auth, bff
from app.web.common import (
    club_staff, club_storages, csrf_error, fio, is_staff, page_request, pager,
    render, redirect,
)

router = APIRouter(include_in_schema=False)


# ---------- transfers ----------
def _transfer_targets(item: Optional[dict], storages: list) -> list:
    """Storages of the item's own club except the one it is in now."""
    if not item:
        return []
    club_id = item.get("club_id")
    current_id = item.get("storage_id")
    return [
        storage for storage in club_storages(storages, club_id)
        if storage["id"] != current_id
    ]


@router.get("/app/transfers")
async def transfers_page(
    request: Request,
    user: dict = Depends(auth.require_user),
    item_id: Optional[int] = None,
):
    if not is_staff(user):
        return render(request, "tourist.html", user=user)

    token = auth.session_token(request)
    page, skip, limit = page_request(request)
    _, items = await bff.get("/api/items/", token, limit=1000)
    _, storages = await bff.get("/api/storages/", token, limit=1000)
    _, users = await bff.get("/api/users/", token, limit=1000)
    _, transfers = await bff.get(
        "/api/transfers/", token, skip=skip, limit=limit)

    items = items if isinstance(items, list) else []
    storages = storages if isinstance(storages, list) else []
    users = users if isinstance(users, list) else []
    transfers = transfers if isinstance(transfers, list) else []

    items_by_id = {item["id"]: item for item in items}
    storage_names = {storage["id"]: storage["name"] for storage in storages}
    user_names = {entry["id"]: fio(entry) for entry in users}

    selected_item = items_by_id.get(item_id) if item_id else None
    if selected_item is None and items:
        selected_item = items[0]
    targets = _transfer_targets(selected_item, storages)

    pager_data = pager(transfers, page, "/app/transfers")
    rows = []
    for record in pager_data["rows"]:
        rows.append({
            **record,
            "item_name": items_by_id.get(record["item_id"], {}).get("name", ""),
            "from_name": storage_names.get(record.get("from_storage_id"), ""),
            "to_name": storage_names.get(record.get("to_storage_id"), ""),
            "mover_name": user_names.get(record.get("mover_id"), ""),
            "receiver_name": user_names.get(record.get("receiver_id"), ""),
        })

    return render(
        request, "transfers.html", user=user, active="transfers",
        items=items, selected_item=selected_item, targets=targets,
        from_name=storage_names.get(selected_item.get("storage_id"), "")
        if selected_item else "",
        storage_names=storage_names, rows=rows, pager=pager_data,
        today=date.today().isoformat(),
    )


@router.get("/app/transfers/targets")
async def transfer_targets_fragment(
    request: Request,
    item_id: Optional[int] = None,
    user: dict = Depends(auth.require_user),
):
    """HTMX fragment: the fixed source storage and the allowed destinations."""
    token = auth.session_token(request)
    _, items = await bff.get("/api/items/", token)
    _, storages = await bff.get("/api/storages/", token)

    items_by_id = {item["id"]: item for item in (items or [])}
    selected = items_by_id.get(item_id)
    storages = storages if isinstance(storages, list) else []
    storage_names = {storage["id"]: storage["name"] for storage in storages}

    return render(
        request, "_transfer_targets.html",
        targets=_transfer_targets(selected, storages),
        from_name=storage_names.get(selected.get("storage_id"), "") if selected else "",
    )


@router.post("/app/transfers")
async def create_transfer(
    request: Request,
    item_id: int = Form(...),
    to_storage_id: int = Form(...),
    comment: str = Form(""),
    csrf_token: str = Form(""),
    user: dict = Depends(auth.require_user),
):
    if not auth.check_csrf(request, csrf_token):
        return csrf_error(request)
    if not is_staff(user):
        return redirect("/app/transfers", error="Недостаточно прав")

    token = auth.session_token(request)
    status, item = await bff.get(f"/api/items/{item_id}", token)
    if status != 200 or not isinstance(item, dict):
        return redirect("/app/transfers", item_id=item_id,
                        error=bff.error_detail(item, "Вещь не найдена"))

    payload = {
        "item_id": item_id,
        "from_storage_id": item.get("storage_id"),
        "to_storage_id": to_storage_id,
        "date": date.today().isoformat(),
        # The person moving the item is always the logged-in user
        "mover_id": user["id"],
    }
    if comment.strip():
        payload["comment"] = comment.strip()

    status, data = await bff.post("/api/transfers/", token, payload)
    if status != 201:
        return redirect("/app/transfers", item_id=item_id,
                        error=bff.error_detail(data))
    return redirect("/app/transfers", ok="transferred")


# ---------- breakdowns ----------
@router.get("/app/breakdowns")
async def breakdowns_page(
    request: Request,
    user: dict = Depends(auth.require_user),
    item_id: Optional[int] = None,
):
    if not is_staff(user):
        return render(request, "tourist.html", user=user)

    token = auth.session_token(request)
    page, skip, limit = page_request(request)
    _, items = await bff.get("/api/items/", token, limit=1000)
    _, users = await bff.get("/api/users/", token, limit=1000)
    _, breakdowns = await bff.get(
        "/api/breakdowns/", token, skip=skip, limit=limit)

    items = items if isinstance(items, list) else []
    users = users if isinstance(users, list) else []
    breakdowns = breakdowns if isinstance(breakdowns, list) else []

    items_by_id = {item["id"]: item for item in items}
    user_names = {entry["id"]: fio(entry) for entry in users}

    selected_item = items_by_id.get(item_id) if item_id else None
    if selected_item is None and items:
        selected_item = items[0]
    repairers = club_staff(users, selected_item.get("club_id") if selected_item else None)

    pager_data = pager(breakdowns, page, "/app/breakdowns")
    rows = []
    for record in pager_data["rows"]:
        rows.append({
            **record,
            "item_name": items_by_id.get(record["item_id"], {}).get("name", ""),
            "repairer_name": user_names.get(record.get("repairer_id"), ""),
        })

    return render(
        request, "breakdowns.html", user=user, active="breakdowns",
        items=items, selected_item=selected_item, repairers=repairers,
        rows=rows, pager=pager_data, today=date.today().isoformat(),
    )


@router.get("/app/breakdowns/repairers")
async def repairers_fragment(
    request: Request,
    item_id: Optional[int] = None,
    user: dict = Depends(auth.require_user),
):
    """HTMX fragment: staff of the selected item's club."""
    token = auth.session_token(request)
    _, items = await bff.get("/api/items/", token)
    _, users = await bff.get("/api/users/", token)

    items_by_id = {item["id"]: item for item in (items or [])}
    selected = items_by_id.get(item_id)
    club_id = selected.get("club_id") if selected else None
    repairers = club_staff(users or [], club_id)

    return render(request, "_repairer_select.html", repairers=repairers)


@router.post("/app/breakdowns")
async def report_breakdown(
    request: Request,
    item_id: int = Form(...),
    comment: str = Form(...),
    repairer_id: Optional[int] = Form(None),
    csrf_token: str = Form(""),
    user: dict = Depends(auth.require_user),
):
    if not auth.check_csrf(request, csrf_token):
        return csrf_error(request)
    if not is_staff(user):
        return redirect("/app/breakdowns", error="Недостаточно прав")

    if not comment.strip():
        return redirect("/app/breakdowns", item_id=item_id,
                        error="Опишите поломку")

    payload = {
        "item_id": item_id,
        "comment": comment.strip(),
        "date": date.today().isoformat(),
        "repairer_id": repairer_id or None,
    }

    status, data = await bff.post(
        "/api/breakdowns/", auth.session_token(request), payload)
    if status != 201:
        return redirect("/app/breakdowns", item_id=item_id,
                        error=bff.error_detail(data))
    return redirect("/app/breakdowns", ok="breakdown_reported")


@router.post("/app/breakdowns/{breakdown_id}/repair")
async def repair_breakdown(
    request: Request,
    breakdown_id: int,
    repaired_date: str = Form(""),
    csrf_token: str = Form(""),
    user: dict = Depends(auth.require_user),
):
    if not auth.check_csrf(request, csrf_token):
        return csrf_error(request)
    if not is_staff(user):
        return redirect("/app/breakdowns", error="Недостаточно прав")

    from app.web.common import parse_date

    payload = {
        # The repairer is always the logged-in user
        "repairer_id": user["id"],
        "repaired_date": parse_date(repaired_date, date.today()),
    }
    status, data = await bff.post(
        f"/api/breakdowns/{breakdown_id}/repair",
        auth.session_token(request), payload)
    if status != 200:
        return redirect("/app/breakdowns", error=bff.error_detail(data))
    return redirect("/app/breakdowns", ok="breakdown_repaired")
