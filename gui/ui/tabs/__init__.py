from PyQt6.QtWidgets import QWidget, QVBoxLayout, QGroupBox, QFormLayout


class BaseTab(QWidget):
    def __init__(self):
        super().__init__()
        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

    def refresh_combos(self):
        """Reload dropdown data that could have changed in other tabs.

        Called when the tab becomes visible. Override in tabs that have
        dropdowns with cross-tab data (clubs, users, items, ...).
        """
        pass

    def create_form_group(self, title):
        group = QGroupBox(title)
        layout = QFormLayout()
        group.setLayout(layout)
        return group