from PyQt6.QtWidgets import QWidget, QVBoxLayout, QGroupBox, QFormLayout


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
