from PyQt6.QtWidgets import (
    QPushButton, QLabel, QLineEdit, QTableWidget, QTableWidgetItem, QMessageBox
)
from gui.api.client import APIClient
from . import BaseTab


class ClubsTab(BaseTab):
    def __init__(self):
        super().__init__()
        self.init_ui()
        self.load_clubs()

    def init_ui(self):
        form_group = self.create_form_group("Добавить клуб")
        form = form_group.layout()

        self.club_name_input = QLineEdit()
        self.club_name_input.setPlaceholderText("Название клуба")
        form.addRow("Название:", self.club_name_input)

        add_btn = QPushButton("Добавить клуб")
        add_btn.clicked.connect(self.add_club)
        form.addRow(add_btn)

        self.layout.addWidget(form_group)

        self.clubs_table = QTableWidget()
        self.clubs_table.setColumnCount(2)
        self.clubs_table.setHorizontalHeaderLabels(["ID", "Название"])
        self.layout.addWidget(QLabel("Список клубов:"))
        self.layout.addWidget(self.clubs_table)

        refresh_btn = QPushButton("Обновить")
        refresh_btn.clicked.connect(self.load_clubs)
        self.layout.addWidget(refresh_btn)

    def add_club(self):
        name = self.club_name_input.text().strip()
        if not name:
            QMessageBox.warning(self, "Ошибка", "Введите название клуба")
            return

        try:
            response = APIClient.post("/clubs", {"name": name})
            if response.status_code == 201:
                QMessageBox.information(self, "Успех", "Клуб добавлен")
                self.club_name_input.clear()
                self.load_clubs()
            else:
                QMessageBox.warning(self, "Ошибка", response.json().get("detail", "Ошибка"))
        except Exception as e:
            QMessageBox.critical(self, "Ошибка подключения", str(e))

    def load_clubs(self):
        try:
            response = APIClient.get("/clubs")
            clubs = response.json()
            self.clubs_table.setRowCount(len(clubs))
            for row, club in enumerate(clubs):
                self.clubs_table.setItem(row, 0, QTableWidgetItem(str(club["id"])))
                self.clubs_table.setItem(row, 1, QTableWidgetItem(club["name"]))
        except Exception as e:
            QMessageBox.critical(self, "Ошибка подключения", str(e))