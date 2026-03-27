from PyQt6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QTabWidget

from .tabs.breakdowns_tab import BreakdownsTab
from .tabs.categories_tab import CategoriesTab
from .tabs.clubs_tab import ClubsTab
from .tabs.distributions_tab import DistributionsTab
from .tabs.items_tab import ItemsTab
from .tabs.storages_tab import StoragesTab
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
        self.tabs.addTab(StoragesTab(), "Склады")
        self.tabs.addTab(UsersTab(), 'Туристы')



        main_layout.addWidget(self.tabs)
        central_widget.setLayout(main_layout)