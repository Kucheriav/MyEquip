from PyQt6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QTabWidget, QLabel

from gui.api.client import APIClient
from .tabs.breakdowns_tab import BreakdownsTab
from .tabs.categories_tab import CategoriesTab
from .tabs.clubs_tab import ClubsTab
from .tabs.distributions_tab import DistributionsTab
from .tabs.items_tab import ItemsTab
from .tabs.storekeepers_tab import StorekeepersTab
from .tabs.storages_tab import StoragesTab
from .tabs.transfers_tab import TransfersTab
from .tabs.users_tab import UsersTab


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("MyEquip - Equipment Tracking System")
        self.setGeometry(100, 100, 1400, 900)

        if APIClient.ME is None:
            APIClient.fetch_me()

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout()
        central_widget.setLayout(main_layout)

        self.tabs = QTabWidget()

        # Tabs depend on the role: a leader manages everything, a
        # storekeeper only works with equipment, tourists have no GUI.
        if APIClient.is_leader():
            tab_defs = [
                (ItemsTab, "Снаряга"),
                (DistributionsTab, "Выдача"),
                (BreakdownsTab, "Поломки"),
                (TransfersTab, "Перемещения"),
                (CategoriesTab, "Категории"),
                (StoragesTab, "Склады"),
                (ClubsTab, "Клубы"),
                (UsersTab, "Туристы"),
                (StorekeepersTab, "Завхозы"),
            ]
        elif APIClient.is_staff():
            tab_defs = [
                (ItemsTab, "Снаряга"),
                (DistributionsTab, "Выдача"),
                (BreakdownsTab, "Поломки"),
                (TransfersTab, "Перемещения"),
            ]
        else:
            tab_defs = []

        for tab_class, title in tab_defs:
            self.tabs.addTab(tab_class(), title)

        if not tab_defs:
            user = APIClient.ME or {}
            name = f"{user.get('surname', '')} {user.get('name', '')}".strip()
            label = QLabel(
                f"Здравствуйте, {name}!\n\n"
                "У вашей учётной записи нет доступа к управлению снаряжением.\n"
                "Обратитесь к руководителю клуба."
            )
            label.setStyleSheet("font-size: 12pt; padding: 24px;")
            main_layout.addWidget(label)
        else:
            main_layout.addWidget(self.tabs)
            # Rebuild dropdowns of a tab when it becomes visible: data added
            # in another tab (a new club, user, item...) must appear in them.
            self.tabs.currentChanged.connect(self.on_tab_changed)

    def on_tab_changed(self, index: int):
        tab = self.tabs.widget(index)
        if hasattr(tab, "refresh_combos"):
            tab.refresh_combos()
