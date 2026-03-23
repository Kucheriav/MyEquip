from PyQt6.QtWidgets import (
    QPushButton, QLabel, QLineEdit, QTableWidget, QTableWidgetItem, QMessageBox
)
from PyQt6.QtCore import Qt
from api.client import APIClient
from . import BaseTab


class ClubsTab(BaseTab):
    def __init__(self):
        super().__init__()
        self.init_ui()
        self.load_clubs()

    def init_ui(self):