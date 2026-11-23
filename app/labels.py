"""Human-readable labels shared by the web UI (and reusable by the GUI).

Status codes are stored in the DB in English; both clients show them in
Russian. Keeping the dictionaries here means the desktop GUI and the web
app cannot drift apart.
"""

STATUS_LABELS = {
    # Item / distribution statuses
    "available": "Доступен",
    "issued": "Выдан",
    "extended": "Продлён",
    "maintenance": "В ремонте",
    "lost": "Потерян",
    "returned": "Возвращён",
    # User statuses
    "guest": "Гость",
    "unverified": "Не подтверждён",
    "full": "Подтверждён",
}

ROLE_LABELS = {
    "leader": "Руководитель",
    "storekeeper": "Завхоз",
    "tourist": "Турист",
}

STAFF_ROLES = ("leader", "storekeeper")

# Statuses a user can pick in a form, in display order
ITEM_STATUSES = ("available", "issued", "maintenance", "lost")
USER_STATUSES = (
    ("guest", STATUS_LABELS["guest"]),
    ("unverified", STATUS_LABELS["unverified"]),
    ("full", STATUS_LABELS["full"]),
)


def translate_status(status):
    return STATUS_LABELS.get(status, status if isinstance(status, str) else "")


def translate_role(role):
    return ROLE_LABELS.get(role, role if isinstance(role, str) else "")
