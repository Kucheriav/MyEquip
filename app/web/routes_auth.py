"""Login, logout and invite-based registration."""
from __future__ import annotations

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from app.web import auth, bff
from app.web.common import render, safe_next

router = APIRouter(include_in_schema=False)


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
