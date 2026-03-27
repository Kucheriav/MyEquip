from PyQt6.QtWidgets import (
    QPushButton, QLabel, QLineEdit, QTableWidget, QTableWidgetItem, QMessageBox, QComboBox
)
from gui.api.client import APIClient
from . import BaseTab


class StoragesTab(BaseTab):
    def __init__(self):
        super().__init__()
        self.init_ui()
        # self.load_clubs()
        # self.load_clubs_combo()
        # self.load_storages()

    def init_ui(self):
        form_group = self.create_form_group("Добавить склад")
        form = form_group.layout()

        self.storage_name_input = QLineEdit()
        self.storage_name_input.setPlaceholderText("Название склада")
        form.addRow("Название:", self.storage_name_input)

        self.storage_address_input = QLineEdit()
        self.storage_address_input.setPlaceholderText("Адрес")
        form.addRow("Адрес:", self.storage_address_input)

        self.storage_club_combo = QComboBox()
        form.addRow("Клуб:", self.storage_club_combo)

        add_storage_btn = QPushButton("Добавить склад")
        add_storage_btn.clicked.connect(self.add_storage)
        form.addRow(add_storage_btn)

        self.layout.addWidget(form_group)

        self.storages_table = QTableWidget()
        self.storages_table.setColumnCount(4)
        self.storages_table.setHorizontalHeaderLabels(["ID", "Название", "Адрес", "Клуб"])
        self.layout.addWidget(QLabel("Список складов:"))
        self.layout.addWidget(self.storages_table)

        refresh_btn = QPushButton("Обновить")
        refresh_btn.clicked.connect(lambda: [self.load_clubs_combo(), self.load_storages()])
        self.layout.addWidget(refresh_btn)

    def load_clubs_combo(self):
        try:
            response = APIClient.get("/clubs")
            clubs = response.json()
            self.storage_club_combo.clear()
            for club in clubs:
                self.storage_club_combo.addItem(club["name"], club["id"])
        except:
            pass

    def add_storage(self):
        name = self.storage_name_input.text().strip()
        address = self.storage_address_input.text().strip()
        club_id = self.storage_club_combo.currentData()

        if not name or not club_id:
            QMessageBox.warning(self, "Ошибка", "Заполните все обязательные поля")
            return
        try:
            response = APIClient.post("/storages", {"name": name, "address": address, "club_id": club_id})
            if response.status_code == 201:
                QMessageBox.information(self, "Успех", "Склад добавлен")
                self.storage_name_input.clear()
                self.storage_address_input.clear()
                self.load_storages()
            else:
                QMessageBox.warning(self, "Ошибка", response.json().get("detail", "Ошибка"))
        except Exception as e:
            QMessageBox.critical(self, "Ошибка подключения", str(e))

    def load_storages(self):
        try:
            response = APIClient.get("/storages")
            storages = response.json()
            self.storages_table.setRowCount(len(storages))
            for row, storage in enumerate(storages):
                self.storages_table.setItem(row, 0, QTableWidgetItem(str(storage["id"])))
                self.storages_table.setItem(row, 1, QTableWidgetItem(storage["name"]))
                self.storages_table.setItem(row, 2, QTableWidgetItem(storage.get("address", "")))
                # Get club name
                try:
                    club_resp = APIClient.get(f"/clubs/{storage['club_id']}")
                    club_name = club_resp.json().get("name", "")
                    self.storages_table.setItem(row, 3, QTableWidgetItem(club_name))
                except:
                    self.storages_table.setItem(row, 3, QTableWidgetItem(""))
        except Exception as e:
            QMessageBox.critical(self, "Ошибка подключения", str(e))


