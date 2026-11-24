"""File logging for the server.

Three streams, all rotating daily and kept for LOG_RETENTION_DAYS:

* ``app.log``      - everything at LOG_LEVEL and above (expected 4xx, slow
                     requests, startup messages)
* ``errors.log``   - ERROR and above, with tracebacks
* ``security.log`` - sign-in attempts, 401/403 and CSRF rejections

Log lines are plain text so they stay greppable on the server. Every
request gets a short id that is also returned in the ``X-Request-ID``
response header, which makes a user's report easy to find in the logs.
"""
from __future__ import annotations

import logging
import logging.handlers
import sys
from pathlib import Path
from typing import Optional

from app.config import config

LOGGER_FORMAT = "%(asctime)s %(levelname)s %(name)s %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Dedicated logger for authentication and access-control events.
security_logger = logging.getLogger("app.security")
access_logger = logging.getLogger("app.access")

_configured = False


class _RequestIdFilter(logging.Filter):
    """Give every record a request_id so the format string always works."""

    def filter(self, record: logging.LogRecord) -> bool:
        if not getattr(record, "request_id", None):
            record.request_id = "-"
        return True


def log_directory() -> Path:
    path = Path(config.LOG_DIR)
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    return path


def _make_handler(path: Path, level: int,
                  fmt: logging.Formatter) -> logging.Handler:
    handler = logging.handlers.TimedRotatingFileHandler(
        path,
        when="midnight",
        backupCount=max(1, config.LOG_RETENTION_DAYS),
        encoding="utf-8",
        delay=True,
    )
    handler.setLevel(level)
    handler.setFormatter(fmt)
    handler.addFilter(_RequestIdFilter())
    return handler


def setup_logging() -> Path:
    """Configure root/uvicorn file logging once. Returns the log folder."""
    global _configured
    directory = log_directory()
    directory.mkdir(parents=True, exist_ok=True)
    if _configured:
        return directory

    level = getattr(logging, config.LOG_LEVEL.upper(), logging.INFO)
    # request_id is ":"-wrapped so grep 'req:ab12' finds one request.
    fmt = logging.Formatter(
        "%(asctime)s %(levelname)s %(name)s req=%(request_id)s %(message)s",
        datefmt=DATE_FORMAT,
    )

    app_handler = _make_handler(directory / "app.log", level, fmt)
    error_handler = _make_handler(directory / "errors.log", logging.ERROR, fmt)
    security_handler = _make_handler(directory / "security.log", logging.INFO, fmt)

    console = logging.StreamHandler(sys.stdout)
    console.setLevel(level)
    console.setFormatter(fmt)
    console.addFilter(_RequestIdFilter())

    root = logging.getLogger()
    root.setLevel(level)
    for handler in list(root.handlers):
        root.removeHandler(handler)
    root.addHandler(console)
    root.addHandler(app_handler)
    root.addHandler(error_handler)

    security_logger.setLevel(logging.INFO)
    security_logger.propagate = False
    security_logger.handlers = [security_handler]

    # Uvicorn configures its own loggers before importing the app. Send its
    # startup/error messages to the same files and disable the per-request
    # access log: we log errors and slow requests ourselves instead.
    uvicorn_error = logging.getLogger("uvicorn.error")
    uvicorn_error.handlers = [console, app_handler, error_handler]
    uvicorn_error.propagate = False

    uvicorn_access = logging.getLogger("uvicorn.access")
    uvicorn_access.handlers = []
    uvicorn_access.propagate = False
    uvicorn_access.disabled = True

    # httpx logs every internal BFF call at INFO; that would drown the log.
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)

    _configured = True
    logging.getLogger(__name__).info(
        "logging to %s (level=%s, keep %s days)",
        directory, config.LOG_LEVEL.upper(), config.LOG_RETENTION_DAYS,
    )
    return directory


def client_ip(request) -> str:
    """Caller address; honours X-Forwarded-For only behind a trusted proxy."""
    if config.TRUST_PROXY:
        forwarded = request.headers.get("x-forwarded-for", "")
        if forwarded:
            return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "-"


def mask_login(value: Optional[str]) -> str:
    """Hide most of a phone/email before it goes into the security log."""
    value = (value or "").strip()
    if not value:
        return "-"
    if "@" in value:
        name, _, domain = value.partition("@")
        return f"{name[:1]}***@{domain}" if name else f"***@{domain}"
    digits = "".join(ch for ch in value if ch.isdigit())
    if len(digits) >= 4:
        return f"***{digits[-4:]}"
    return "***"
