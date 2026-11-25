"""Equipment photo files on disk.

The database stores only the relative path (``items/<item_id>/<name>``);
all files live under ``DATA_DIR/uploads``. Keeping the two apart makes a
backup of the data folder self-contained and lets the folder move between
machines without touching the database.

Only real images are accepted: the content type sent by the browser is
easy to fake, so the first bytes are checked against the JPEG, PNG and
WebP signatures. SVG is intentionally not allowed (it can carry scripts).
"""
from __future__ import annotations

import logging
import uuid
from pathlib import Path
from typing import Iterable, Optional

from app.config import config

logger = logging.getLogger("app.photos")

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Enough to document an item without turning the card into a gallery dump.
# The actual limit comes from config so deployment can tune it.


def max_per_item() -> int:
    return max(1, config.PHOTO_MAX_PER_ITEM)
_SIGNATURES = (
    (b"\xff\xd8\xff", "jpg", "image/jpeg"),
    (b"\x89PNG\r\n\x1a\n", "png", "image/png"),
)


def uploads_root() -> Path:
    path = Path(config.DATA_DIR)
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    return path / "uploads"


def item_dir(item_id: int) -> Path:
    return uploads_root() / "items" / str(item_id)


def max_photo_bytes() -> int:
    return max(1, config.PHOTO_MAX_MB) * 1024 * 1024


def detect_image(data: bytes) -> Optional[tuple[str, str]]:
    """(extension, content type) for a supported image, otherwise None."""
    for signature, extension, content_type in _SIGNATURES:
        if data.startswith(signature):
            return extension, content_type
    if len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "webp", "image/webp"
    return None


def save_photo(item_id: int, data: bytes, extension: str) -> str:
    """Write the file and return its path relative to the uploads root."""
    directory = item_dir(item_id)
    directory.mkdir(parents=True, exist_ok=True)
    name = f"{uuid.uuid4().hex}.{extension}"
    (directory / name).write_bytes(data)
    return f"items/{item_id}/{name}"


def photo_path(relative_path: str) -> Path:
    return uploads_root() / Path(relative_path)


def unlink(relative_paths: Iterable[str]) -> None:
    """Best-effort file removal: the database row is the source of truth."""
    for relative_path in relative_paths:
        try:
            photo_path(relative_path).unlink(missing_ok=True)
        except OSError:
            logger.warning(
                "could not delete photo file %s", relative_path, exc_info=True)
