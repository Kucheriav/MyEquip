from PyQt6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QTabWidget
from PyQt6.QtGui import QIcon
from .tabs.clubs_tab import ClubsTab
from .tabs.storages_tab import StoragesTab


# ... остальные импорты

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("MyEquip - Equipment Tracking System")
        self.setGeometry(100, 100, 1400, 900)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout()

        self.tabs = QTabWidget()
        self.tabs.addTab(ClubsTab(), "Клубы")
        self.tabs.addTab(StoragesTab(), "Склады")
        # ... остальные вкладки

        main_layout.addWidget(self.tabs)
        central_widget.setLayout(main_layout)