from PyQt6.QtWidgets import QWidget, QVBoxLayout, QGroupBox, QFormLayout

# Status codes are stored in the DB in English; the GUI shows them in
# Russian. Covers item statuses (items, distributions) and user statuses.
STATUS_LABELS = {
    "available": "Доступен",
    "issued": "Выдан",
    "maintenance": "В ремонте",
    "lost": "Потерян",
    "returned": "Возвращён",
    "guest": "Гость",
    "unverified": "Не подтверждён",
    "full": "Подтверждён",
}


ROLE_LABELS = {
    "leader": "Руководитель",
    "storekeeper": "Завхоз",
    "tourist": "Турист",
}


def translate_status(status):
    return STATUS_LABELS.get(status, status if isinstance(status, str) else "")


def translate_role(role):
    return ROLE_LABELS.get(role, role if isinstance(role, str) else "")


# Roles that may perform equipment operations (issue, accept, move)
STAFF_ROLES = ("leader", "storekeeper")


def club_role(user: dict, club_id):
    """The user's role inside one club (or None if they are not a member)."""
    for membership in user.get("memberships") or []:
        if membership.get("club_id") == club_id:
            return membership.get("role")
    return None


def users_of_club(users, club_id, staff_only: bool = False):
    """Club members (optionally only leader/storekeeper)."""
    if club_id is None:
        return []
    result = []
    for user in users:
        role = club_role(user, club_id)
        if role is None:
            continue
        if staff_only and role not in STAFF_ROLES:
            continue
        result.append(user)
    return result


def current_user_id():
    """ID of the logged-in user — they always perform the operation
    themselves, so giver/accepter/mover are never chosen in the GUI."""
    from gui.api.client import APIClient

    return (APIClient.ME or {}).get("id")


def fill_user_combo(combo, users, preferred_id=None, keep_current: bool = True):
    """Fill a combo with users, keeping the selection when possible.
    Falls back to preferred_id (usually the logged-in user)."""
    from gui.api.client import APIClient

    current = combo.currentData() if keep_current else None
    combo.blockSignals(True)
    combo.clear()
    for user in users:
        fio = f"{user['surname']} {user['name']}"
        combo.addItem(fio, user["id"])
    target = current if current is not None else (
        preferred_id if preferred_id is not None else (APIClient.ME or {}).get("id"))
    index = combo.findData(target) if target is not None else -1
    if index >= 0:
        combo.setCurrentIndex(index)
    combo.blockSignals(False)


class BaseTab(QWidget):
    def __init__(self):
        super().__init__()
        self.layout = QVBoxLayout()
        self.setLayout(self.layout)
        # Lazy loading: the full data load happens on the first show of the
        # tab, not at window construction. Otherwise opening the window
        # would load every tab at once.
        self._loaded = False

    # ---------- lazy load ----------
    def load_data(self):
        """Full data load (combos + table). Override in tabs.

        Runs exactly once, when the tab becomes visible for the first
        time; later updates go through the 'Обновить' button and after
        successful record creation.
        """
        pass

    def showEvent(self, event):
        if not self._loaded:
            self._loaded = True
            self.load_data()
        super().showEvent(event)

    # ---------- cross-tab dropdown freshness ----------
    def refresh_combos(self):
        """Reload dropdown data that could have changed in other tabs.

        Called on every tab switch. Keep it light: dropdowns only,
        no table rebuilds.
        """
        pass

    # ---------- helpers ----------
    @staticmethod
    def fetch_lookup(path: str, key: str, value):
        """GET a list endpoint and return {id: value} for cheap name lookups
        (avoids one HTTP request per table row)."""
        from gui.api.client import APIClient
        try:
            rows = APIClient.get(path).json()
            return {row["id"]: value(row) for row in rows}
        except Exception:
            return {}

    def create_form_group(self, title):
        group = QGroupBox(title)
        layout = QFormLayout()
        group.setLayout(layout)
        return group
