"""First-run bootstrap: when the database has no users at all, generate
one invite code and write it to invite_code.txt in the project root so
that the very first leader can register."""
import logging
import os

from app.database import SessionLocal
from app.models import User
from app.services import invite_service

logger = logging.getLogger("app.bootstrap")

INVITE_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "invite_code.txt",
)


def bootstrap_invite_if_empty():
    db = SessionLocal()
    try:
        has_users = db.query(User.id).first() is not None
        if has_users:
            return

        invite = invite_service.generate_code(db, created_by=None)
        with open(INVITE_FILE, "w", encoding="utf-8") as f:
            f.write(
                "MyEquip invite code (one-time, for the first leader registration)\n"
                f"{invite.code}\n"
                f"created: {invite.created_at}\n"
            )
        logger.info(
            "Empty database: bootstrap invite code generated and written to %s",
            INVITE_FILE,
        )
        print(f"[bootstrap] invite code for the first leader: {invite.code} -> {INVITE_FILE}")
    finally:
        db.close()
