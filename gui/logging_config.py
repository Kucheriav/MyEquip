"""Local file logging for the desktop client.

Qt exceptions that happen inside a slot may kill the process without a
traceback on the console, so the client writes its own log and installs
an excepthook. The path can be overridden with MYEQUIP_GUI_LOG_DIR;
otherwise %APPDATA%\\MyEquip\\logs is used on Windows.
"""
from __future__ import annotations

import logging
import logging.handlers
import os
import sys
import threading
from pathlib import Path

LOGGER_FORMAT = "%(asctime)s %(levelname)s %(name)s %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
RETENTION_DAYS = 14

_configured = False


def gui_log_directory() -> Path:
    override = os.environ.get("MYEQUIP_GUI_LOG_DIR")
    if override:
        return Path(override)
    appdata = os.environ.get("APPDATA")
    if appdata:
        return Path(appdata) / "MyEquip" / "logs"
    return Path.home() / ".myequip" / "logs"


def _install_hooks() -> None:
    previous = sys.excepthook
    logger = logging.getLogger("gui")

    def excepthook(exc_type, exc, tb):
        logger.critical("Unhandled exception", exc_info=(exc_type, exc, tb))
        previous(exc_type, exc, tb)

    sys.excepthook = excepthook

    previous_thread_hook = threading.excepthook

    def thread_excepthook(args):
        logger.critical(
            "Unhandled exception in thread %s",
            getattr(args.thread, "name", "?"),
            exc_info=(args.exc_type, args.exc_value, args.exc_traceback),
        )
        previous_thread_hook(args)

    threading.excepthook = thread_excepthook


def setup_gui_logging() -> Path:
    """Configure the client log once and return the folder it lives in."""
    global _configured
    directory = gui_log_directory()
    directory.mkdir(parents=True, exist_ok=True)
    if _configured:
        return directory

    formatter = logging.Formatter(LOGGER_FORMAT, datefmt=DATE_FORMAT)
    handler = logging.handlers.TimedRotatingFileHandler(
        directory / "gui.log",
        when="midnight",
        backupCount=RETENTION_DAYS,
        encoding="utf-8",
        delay=True,
    )
    handler.setFormatter(formatter)

    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.addHandler(handler)

    _install_hooks()
    _configured = True
    logging.getLogger("gui").info("logging to %s", directory / "gui.log")
    return directory
