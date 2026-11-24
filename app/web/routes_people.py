"""People, clubs and access (invites, storekeepers)."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Form, Request

from app import labels
from app.web import auth, bff
from app.web.common import (
    USER_STATUSES, csrf_error, fio, is_leader, is_staff, led_clubs, page_request,
    pager, render, redirect,
)

router = APIRouter(include_in_schema=False)


def _staff_club_ids(user: dict) -> set[int]:
    return {
        membership.get("club_id")
        for membership in user.get("memberships") or []
        if membership.get("role") in labels.STAFF_ROLES
    }


def _staff_clubs(user: dict, clubs: list) -> list:
    allowed = _staff_club_ids(user)
    return [club for club in clubs if club["id"] in allowed]


# ---------- people ----------
@router.get("/app/people")
async def people_page(
    request: Request,
    user: dict = Depends(auth.require_user),
    club_id: Optional[int] = None,
    q: Optional[str] = None,
):
    if not is_staff(user):
        return render(request, "tourist.html", user=user)

    token = auth.session_token(request)
    page, skip, limit = page_request(request)
    _, clubs = await bff.get("/api/clubs/", token)
    code, users = await bff.get(
        "/api/users/", token, club_id=club_id, q=q, skip=skip, limit=limit)

    clubs = clubs if isinstance(clubs, list) else []
    clubs = _staff_clubs(user, clubs)
    users = users if isinstance(users, list) else []
    club_names = {club["id"]: club["name"] for club in clubs}

    pager_data = pager(users, page, "/app/people", q=q, club_id=club_id)
    rows = []
    for entry in pager_data["rows"]:
        memberships = entry.get("memberships") or []
        entry_clubs = ", ".join(
            sorted(
                club_names.get(membership.get("club_id"), f"клуб {membership.get('club_id')}")
                for membership in memberships
            )
        )
        rows.append({**entry, "clubs_text": entry_clubs})

    return render(
        request, "people.html", user=user, active="people",
        rows=rows, pager=pager_data, clubs=clubs, club_names=club_names,
        led_club_ids=led_clubs(user), statuses=USER_STATUSES,
        selected_club_id=club_id, q=q or "",
        api_error=bff.error_detail(users) if code >= 400 else None,
    )


@router.post("/app/people")
async def create_person(
    request: Request,
    club_id: int = Form(...),
    name: str = Form(...),
    surname: str = Form(...),
    phone: str = Form(...),
    last_name: str = Form(""),
    email: str = Form(""),
    date_of_birth: str = Form(""),
    status: str = Form("guest"),
    csrf_token: str = Form(""),
    user: dict = Depends(auth.require_user),
):
    if not auth.check_csrf(request, csrf_token):
        return csrf_error(request)
    if not is_leader(user):
        return redirect("/app/people", error="Добавлять людей может только руководитель")

    payload = {
        "club_id": club_id,
        "name": name.strip(),
        "surname": surname.strip(),
        "phone": phone.strip(),
        "status": status,
    }
    if last_name.strip():
        payload["last_name"] = last_name.strip()
    if email.strip():
        payload["email"] = email.strip()
    if date_of_birth.strip():
        payload["date_of_birth"] = date_of_birth.strip()

    status_code, data = await bff.post(
        "/api/users/", auth.session_token(request), payload)
    if status_code != 201:
        return redirect("/app/people", error=bff.error_detail(data))
    return redirect("/app/people", ok="person_created")


@router.get("/app/people/{person_id}/edit")
async def edit_person_page(
    request: Request,
    person_id: int,
    user: dict = Depends(auth.require_user),
):
    if not is_leader(user):
        return render(request, "tourist.html", user=user)

    token = auth.session_token(request)
    code, person = await bff.get(f"/api/users/{person_id}", token)
    if code != 200 or not isinstance(person, dict):
        return redirect("/app/people", error=bff.error_detail(person, "Человек не найден"))

    _, clubs = await bff.get("/api/clubs/", token)
    club_names = {club["id"]: club["name"] for club in (clubs or [])}
    memberships = ", ".join(
        f"{club_names.get(m.get('club_id'), 'клуб')} — {labels.translate_role(m.get('role'))}"
        for m in person.get("memberships") or []
    )

    return render(
        request, "person_edit.html", user=user, active="people",
        person=person, statuses=USER_STATUSES, memberships_text=memberships,
    )


@router.post("/app/people/{person_id}")
async def update_person(
    request: Request,
    person_id: int,
    name: str = Form(...),
    surname: str = Form(...),
    phone: str = Form(...),
    last_name: str = Form(""),
    email: str = Form(""),
    date_of_birth: str = Form(""),
    status: str = Form("guest"),
    csrf_token: str = Form(""),
    user: dict = Depends(auth.require_user),
):
    if not auth.check_csrf(request, csrf_token):
        return csrf_error(request)
    if not is_leader(user):
        return redirect("/app/people", error="Менять данные может только руководитель")

    payload = {
        "name": name.strip(),
        "surname": surname.strip(),
        "phone": phone.strip(),
        "status": status,
        "last_name": last_name.strip() or None,
        "email": email.strip() or None,
        "date_of_birth": date_of_birth.strip() or None,
    }
    status_code, data = await bff.put(
        f"/api/users/{person_id}", auth.session_token(request), payload)
    if status_code != 200:
        return redirect(f"/app/people/{person_id}/edit",
                        error=bff.error_detail(data))
    return redirect("/app/people", ok="person_updated")


# ---------- clubs ----------
@router.get("/app/clubs")
async def clubs_page(
    request: Request,
    user: dict = Depends(auth.require_user),
):
    if not is_staff(user):
        return render(request, "tourist.html", user=user)

    token = auth.session_token(request)
    code, clubs = await bff.get("/api/clubs/", token)
    clubs = clubs if isinstance(clubs, list) else []

    rows = []
    for club in clubs:
        memberships = [
            membership.get("role") for membership in user.get("memberships") or []
            if membership.get("club_id") == club["id"]
        ]
        rows.append({
            **club,
            "my_role": memberships[0] if memberships else "",
            "can_manage": "leader" in memberships,
        })

    return render(
        request, "clubs.html", user=user, active="clubs", rows=rows,
        api_error=bff.error_detail(clubs) if code >= 400 else None,
    )


@router.post("/app/clubs")
async def create_club(
    request: Request,
    name: str = Form(...),
    csrf_token: str = Form(""),
    user: dict = Depends(auth.require_user),
):
    if not auth.check_csrf(request, csrf_token):
        return csrf_error(request)
    if not is_leader(user):
        return redirect("/app/clubs", error="Создавать клубы может только руководитель")

    if not name.strip():
        return redirect("/app/clubs", error="Укажите название клуба")

    status, data = await bff.post(
        "/api/clubs/", auth.session_token(request), {"name": name.strip()})
    if status != 201:
        return redirect("/app/clubs", error=bff.error_detail(data))
    return redirect("/app/clubs", ok="club_created")


# ---------- access: invites and storekeepers ----------
@router.get("/app/team")
async def team_page(
    request: Request,
    user: dict = Depends(auth.require_user),
    club_id: Optional[int] = None,
):
    if not is_leader(user):
        return render(request, "tourist.html", user=user)

    token = auth.session_token(request)
    _, clubs = await bff.get("/api/clubs/", token)
    _, users = await bff.get("/api/users/", token)
    _, invites = await bff.get("/api/invites/", token)

    clubs = clubs if isinstance(clubs, list) else []
    users = users if isinstance(users, list) else []
    invites = invites if isinstance(invites, list) else []

    led_ids = led_clubs(user)
    led = [club for club in clubs if club["id"] in led_ids]
    club_names = {club["id"]: club["name"] for club in clubs}

    selected_club_id = club_id if club_id in led_ids else (led[0]["id"] if led else None)
    members = []
    if selected_club_id:
        _, members = await bff.get(
            f"/api/clubs/{selected_club_id}/members", token)
        members = members if isinstance(members, list) else []

    storekeepers = [member for member in members if member.get("role") == "storekeeper"]

    # Do not offer to demote a leader of the selected club to storekeeper
    grant_candidates = [
        entry for entry in users
        if not any(
            membership.get("club_id") == selected_club_id
            and membership.get("role") == "leader"
            for membership in entry.get("memberships") or []
        )
    ]

    invite_rows = []
    for invite in sorted(invites, key=lambda row: row["id"], reverse=True):
        invite_rows.append({
            **invite,
            "club_name": club_names.get(invite.get("club_id"), "—"),
        })

    created_invite = request.cookies.get(auth.INVITE_FLASH_COOKIE) or ""
    response = render(
        request, "team.html", user=user, active="team",
        clubs=led, club_names=club_names, selected_club_id=selected_club_id,
        storekeepers=storekeepers, users=grant_candidates,
        invites=invite_rows, created_invite=created_invite,
    )
    if created_invite:
        auth.clear_invite_flash(response)
    return response


@router.post("/app/team/invite-storekeeper")
async def invite_storekeeper(
    request: Request,
    club_id: int = Form(...),
    csrf_token: str = Form(""),
    user: dict = Depends(auth.require_user),
):
    if not auth.check_csrf(request, csrf_token):
        return csrf_error(request)
    if not is_leader(user):
        return redirect("/app/team", error="Инвайты создаёт только руководитель")

    status, data = await bff.post(
        "/api/invites/", auth.session_token(request),
        {"role": "storekeeper", "club_id": club_id})
    if status != 201:
        return redirect("/app/team", club_id=club_id, error=bff.error_detail(data))

    response = redirect("/app/team", club_id=club_id, ok="invite_created")
    auth.set_invite_flash(response, data.get("code", ""))
    return response


@router.post("/app/team/invite-leader")
async def invite_leader(
    request: Request,
    csrf_token: str = Form(""),
    user: dict = Depends(auth.require_user),
):
    if not auth.check_csrf(request, csrf_token):
        return csrf_error(request)
    if not is_leader(user):
        return redirect("/app/team", error="Инвайты создаёт только руководитель")

    status, data = await bff.post(
        "/api/invites/", auth.session_token(request), {"role": "leader"})
    if status != 201:
        return redirect("/app/team", error=bff.error_detail(data))

    response = redirect("/app/team", ok="invite_created")
    auth.set_invite_flash(response, data.get("code", ""))
    return response


@router.post("/app/team/storekeepers")
async def grant_storekeeper(
    request: Request,
    club_id: int = Form(...),
    user_id: int = Form(...),
    csrf_token: str = Form(""),
    user: dict = Depends(auth.require_user),
):
    if not auth.check_csrf(request, csrf_token):
        return csrf_error(request)
    if not is_leader(user):
        return redirect("/app/team", error="Назначает завхозов только руководитель")

    status, data = await bff.post(
        f"/api/clubs/{club_id}/members", auth.session_token(request),
        {"user_id": user_id, "role": "storekeeper"})
    if status != 201:
        return redirect("/app/team", club_id=club_id, error=bff.error_detail(data))
    return redirect("/app/team", club_id=club_id, ok="member_added")


@router.post("/app/team/storekeepers/{club_id}/{member_id}/remove")
async def remove_storekeeper(
    request: Request,
    club_id: int,
    member_id: int,
    csrf_token: str = Form(""),
    user: dict = Depends(auth.require_user),
):
    if not auth.check_csrf(request, csrf_token):
        return csrf_error(request)
    if not is_leader(user):
        return redirect("/app/team", error="Убирает из клуба только руководитель")

    status, data = await bff.delete(
        f"/api/clubs/{club_id}/members/{member_id}", auth.session_token(request))
    if status != 204:
        return redirect("/app/team", club_id=club_id, error=bff.error_detail(data))
    return redirect("/app/team", club_id=club_id, ok="member_removed")
