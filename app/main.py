import time
import uuid
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from app.config import config
from app.database import create_all_tables
from app.bootstrap import bootstrap_invite_if_empty
from app.logging_config import (
    access_logger, client_ip, security_logger, setup_logging,
)
from app.routers import (
    user_router, club_router, category_router, parameter_router,
    value_router, storage_router, item_router, distribution_router,
    breakdown_router, item_parameter_value_router, transfer_router,
    auth_router, invite_router,
)
from app.web.auth import WebAuthRequired, login_redirect
from app.web.routes import router as web_router

setup_logging()

# Create FastAPI application
app = FastAPI(
    title="MyEquip API",
    description="Equipment rental and tracking system",
    version="1.0.0"
)

# Add CORS middleware (any local client: PyQt GUI, future web frontend)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Paths that are noisy (probes, static files) or not ours at all
UNLOGGED_PATHS = ("/health", "/favicon.ico")
UNLOGGED_PREFIXES = ("/static/", "/v1/")


def _log_request(request: Request, request_id: str, started: float,
                 status: int, failed: bool = False) -> None:
    path = request.url.path
    if path in UNLOGGED_PATHS or path.startswith(UNLOGGED_PREFIXES):
        return
    elapsed_ms = (time.perf_counter() - started) * 1000
    user_id = getattr(request.state, "user_id", "-")
    ip = client_ip(request)
    extra = {"request_id": request_id}
    if failed:
        access_logger.exception(
            "%s %s -> 500 in %.0f ms user=%s ip=%s",
            request.method, path, elapsed_ms, user_id, ip, extra=extra)
    elif status in (401, 403) and path != "/login":
        # /login failures are already logged by the login handler with a
        # masked identifier; other 401/403s are access-control events.
        security_logger.warning(
            "%s %s -> %s user=%s ip=%s",
            request.method, path, status, user_id, ip, extra=extra)
    elif status >= 500:
        access_logger.error(
            "%s %s -> %s in %.0f ms user=%s ip=%s",
            request.method, path, status, elapsed_ms, user_id, ip, extra=extra)
    elif status >= 400 or elapsed_ms >= config.LOG_SLOW_MS:
        access_logger.warning(
            "%s %s -> %s in %.0f ms user=%s ip=%s",
            request.method, path, status, elapsed_ms, user_id, ip, extra=extra)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log failed and slow requests; hand a request id back to the client."""
    request_id = uuid.uuid4().hex[:12]
    request.state.request_id = request_id
    started = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        _log_request(request, request_id, started, 500, failed=True)
        raise
    _log_request(request, request_id, started, response.status_code)
    response.headers["X-Request-ID"] = request_id
    return response

# Create all database tables, then generate the first invite code if the DB is empty
create_all_tables()
bootstrap_invite_if_empty()

# Include routers
app.include_router(user_router.router)
app.include_router(club_router.router)
app.include_router(category_router.router)
app.include_router(parameter_router.router)
app.include_router(value_router.router)
app.include_router(storage_router.router)
app.include_router(item_router.router)
app.include_router(distribution_router.router)
app.include_router(breakdown_router.router)
app.include_router(item_parameter_value_router.router)
app.include_router(transfer_router.router)
app.include_router(auth_router.router)
app.include_router(invite_router.router)

# Web UI: server-rendered pages that talk to the API above
app.include_router(web_router)
app.mount(
    "/static",
    StaticFiles(directory=str(Path(__file__).parent / "web" / "static")),
    name="static",
)


@app.exception_handler(WebAuthRequired)
async def web_auth_required(request, exc):
    """Pages redirect to the login form; API endpoints keep returning 401."""
    return login_redirect(request)


@app.get("/", tags=["root"], include_in_schema=False)
async def root():
    """Send people to the web UI; the API banner lives at /api."""
    return RedirectResponse("/app/items", status_code=303)


@app.get("/api", tags=["root"])
async def api_root():
    return {
        "message": "MyEquip API",
        "docs": "/docs",
        "openapi_schema": "/openapi.json"
    }


@app.get("/health", tags=["root"])
async def health():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
