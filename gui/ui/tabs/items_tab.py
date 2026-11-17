from PyQt6.QtWidgets import (
    QPushButton, QLabel, QLineEdit, QTableWidget, QTableWidgetItem, QMessageBox, QComboBox
)
from gui.api.client import APIClient
from . import BaseTab


class ItemsTab(BaseTab):
    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        form_group = self.create_form_group("Добавить снаряжение")
        form = form_group.layout()

        self.item_name_input = QLineEdit()
        self.item_name_input.setPlaceholderText("Название предмета")
        form.addRow("Название:", self.item_name_input)

        self.item_category_combo = QComboBox()
        form.addRow("Категория:", self.item_category_combo)

        self.item_storage_combo = QComboBox()
        form.addRow("Склад:", self.item_storage_combo)

        self.item_owner_combo = QComboBox()
        form.addRow("Владелец:", self.item_owner_combo)

        self.item_serial_input = QLineEdit()
        self.item_serial_input.setPlaceholderText("Серийный номер (опционально)")
        form.addRow("Серийный номер:", self.item_serial_input)

        self.item_status_combo = QComboBox()
        self.item_status_combo.addItems(["available", "issued", "maintenance", "lost"])
        form.addRow("Статус:", self.item_status_combo)

        add_item_btn = QPushButton("Добавить предмет")
        add_item_btn.clicked.connect(self.add_item)
        form.addRow(add_item_btn)

        self.layout.addWidget(form_group)

        # Table
        self.items_table = QTableWidget()
        self.items_table.setColumnCount(7)
        self.items_table.setHorizontalHeaderLabels(
            ["ID", "Название", "Категория", "Склад", "Владелец", "Статус", "Серийный"])
        self.layout.addWidget(QLabel("Список снаряжения:"))
        self.layout.addWidget(self.items_table)

        refresh_btn = QPushButton("Обновить")
        refresh_btn.clicked.connect(self.load_items_data)
        self.layout.addWidget(refresh_btn)

    def load_items_data(self):
        self.load_categories_combo()
        self.load_storages_combo()
        self.load_users_combo()
        self.load_items()

    def load_data(self):
        self.load_items_data()

    def refresh_combos(self):
        """Categories, storages and users may have changed in other tabs."""
        self.load_categories_combo()
        self.load_storages_combo()
        self.load_users_combo()

    def load_categories_combo(self):
        try:
            response = APIClient.get("/categories")
            categories = response.json()
            self.item_category_combo.clear()
            for category in categories:
                self.item_category_combo.addItem(category["title"], category["id"])
        except:
            pass

    def load_storages_combo(self):
        try:
            response = APIClient.get("/storages")
            storages = response.json()
            self.item_storage_combo.clear()
            for storage in storages:
                self.item_storage_combo.addItem(storage["name"], storage["id"])
        except:
            pass

    def load_users_combo(self):
        try:
            response = APIClient.get("/users")
            users = response.json()
            self.item_owner_combo.clear()
            for user in users:
                fio = f"{user['surname']} {user['name']}"
                self.item_owner_combo.addItem(fio, user["id"])
        except:
            pass

    def add_item(self):
        name = self.item_name_input.text().strip()
        category_id = self.item_category_combo.currentData()
        storage_id = self.item_storage_combo.currentData()
        owner_id = self.item_owner_combo.currentData()
        serial = self.item_serial_input.text().strip()
        status = self.item_status_combo.currentText()

        if not all([name, category_id, storage_id, owner_id]):
            QMessageBox.warning(self, "Ошибка", "Заполните обязательные поля")
            return

        try:
            data = {
                "name": name,
                "category_id": category_id,
                "storage_id": storage_id,
                "owner_id": owner_id,
                "status": status
            }
            if serial:
                data["serial_number"] = serial

            response = APIClient.post("/items", data)
            if response.status_code == 201:
                QMessageBox.information(self, "Успех", "Снаряжени�� добавлено")
                self.item_name_input.clear()
                self.item_serial_input.clear()
                self.load_items()
            else:
                QMessageBox.warning(self, "Ошибка", response.json().get("detail", "Ошибка"))
        except Exception as e:
            QMessageBox.critical(self, "Ошибка подключения", str(e))

    def load_items(self):
        try:
            # One request per entity instead of one per table row
            cat_names = self.fetch_lookup("/categories", "id", lambda c: c["title"])
            stor_names = self.fetch_lookup("/storages", "id", lambda s: s["name"])
            user_names = self.fetch_lookup("/users", "id", lambda u: f"{u['surname']} {u['name']}")

            response = APIClient.get(f"/items")
            items = response.json()
            self.items_table.setRowCount(len(items))

            for row, item in enumerate(items):
                self.items_table.setItem(row, 0, QTableWidgetItem(str(item["id"])))
                self.items_table.setItem(row, 1, QTableWidgetItem(item["name"]))
                self.items_table.setItem(
                    row, 2, QTableWidgetItem(cat_names.get(item["category_id"], "")))
                self.items_table.setItem(
                    row, 3, QTableWidgetItem(stor_names.get(item["storage_id"], "")))
                self.items_table.setItem(
                    row, 4, QTableWidgetItem(user_names.get(item["owner_id"], "")))

                self.items_table.setItem(row, 5, QTableWidgetItem(item.get("status", "")))
                self.items_table.setItem(row, 6, QTableWidgetItem(item.get("serial_number", "")))
        except Exception as e:
            QMessageBox.critical(self, "Ошибка подключения", str(e))
