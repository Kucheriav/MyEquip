"""Login, logout and invite-based registration."""
from __future__ import annotations

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from app.web import auth, bff
from app.web.common import render, safe_next
from app.logging_config import client_ip, mask_login, security_logger

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
        security_logger.warning(
            "login failed login=%s status=%s ip=%s",
            mask_login(login), status, client_ip(request),
            extra={"request_id": getattr(request.state, "request_id", "-")},
        )
        return render(
            request, "login.html",
            error=bff.error_detail(payload, "Неверный телефон/почта или пароль"),
            login=login, next=safe_next(next), status_code=401)
    security_logger.info(
        "login ok login=%s ip=%s",
        mask_login(login), client_ip(request),
        extra={"request_id": getattr(request.state, "request_id", "-")},
    )
    response = RedirectResponse(safe_next(next), status_code=303)
    auth.start_session(response, payload["access_token"])
    return response


@router.post("/logout")
async def logout(request: Request):
    security_logger.info(
        "logout ip=%s", client_ip(request),
        extra={"request_id": getattr(request.state, "request_id", "-")},
    )
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
        security_logger.warning(
            "register failed login=%s status=%s ip=%s",
            mask_login(phone), status, client_ip(request),
            extra={"request_id": getattr(request.state, "request_id", "-")},
        )
        return render(
            request, "register.html", status_code=400,
            error=bff.error_detail(data, "Не удалось зарегистрироваться"),
            form={"invite_code": invite_code, "name": name, "surname": surname,
                  "phone": phone, "email": email})
    security_logger.info(
        "register ok login=%s ip=%s",
        mask_login(phone), client_ip(request),
        extra={"request_id": getattr(request.state, "request_id", "-")},
    )
    return RedirectResponse("/login?ok=registered", status_code=303)
