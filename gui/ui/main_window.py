from PyQt6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QTabWidget

from .tabs.breakdowns_tab import BreakdownsTab
from .tabs.categories_tab import CategoriesTab
from .tabs.clubs_tab import ClubsTab
from .tabs.distributions_tab import DistributionsTab
from .tabs.items_tab import ItemsTab
from .tabs.storages_tab import StoragesTab
from .tabs.transfers_tab import TransfersTab
from .tabs.users_tab import UsersTab


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("MyEquip - Equipment Tracking System")
        self.setGeometry(100, 100, 1400, 900)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout()

        self.tabs = QTabWidget()
        self.tabs.addTab(BreakdownsTab(), 'Поломки')
        self.tabs.addTab(CategoriesTab(), 'Категории')
        self.tabs.addTab(ClubsTab(), 'Клубы')
        self.tabs.addTab(DistributionsTab(), 'Выдача')
        self.tabs.addTab(ItemsTab(), 'Снаряга')
        self.tabs.addTab(TransfersTab(), 'Перемещения')
        self.tabs.addTab(StoragesTab(), "Склады")
        self.tabs.addTab(UsersTab(), 'Туристы')

        # Rebuild dropdowns of a tab when it becomes visible: data added
        # in another tab (a new club, user, item...) must appear in them.
        self.tabs.currentChanged.connect(self.on_tab_changed)

        main_layout.addWidget(self.tabs)
        central_widget.setLayout(main_layout)

    def on_tab_changed(self, index: int):
        tab = self.tabs.widget(index)
        if hasattr(tab, "refresh_combos"):
            tab.refresh_combos()