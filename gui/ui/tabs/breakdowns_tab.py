from PyQt6.QtWidgets import (
    QPushButton, QLabel, QLineEdit, QTableWidget, QTableWidgetItem, QMessageBox, QComboBox, QDateEdit
)
from PyQt6.QtCore import QDate
from gui.api.client import APIClient
from . import BaseTab


class BreakdownsTab(BaseTab):
    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        form_group = self.create_form_group("Зарегистрировать поломку")
        form = form_group.layout()

        self.breakdown_item_combo = QComboBox()
        form.addRow("Предмет:", self.breakdown_item_combo)

        self.breakdown_comment_input = QLineEdit()
        self.breakdown_comment_input.setPlaceholderText("Описание поломки")
        form.addRow("Описание:", self.breakdown_comment_input)

        self.breakdown_repairer_combo = QComboBox()
        self.breakdown_repairer_combo.addItem("Нет", None)
        form.addRow("Мастер (опционально):", self.breakdown_repairer_combo)

        report_breakdown_btn = QPushButton("Зарегистрировать поломку")
        report_breakdown_btn.clicked.connect(self.report_breakdown)
        form.addRow(report_breakdown_btn)

        self.layout.addWidget(form_group)

        # Table
        self.breakdowns_table = QTableWidget()
        self.breakdowns_table.setColumnCount(7)
        self.breakdowns_table.setHorizontalHeaderLabels(
            ["ID", "Предмет", "Описание", "Дата поломки", "Отремонтирована", "Мастер", "Действие"]
        )
        self.layout.addWidget(QLabel("Список поломок:"))
        self.layout.addWidget(self.breakdowns_table)

        refresh_btn = QPushButton("Обновить")
        refresh_btn.clicked.connect(self.load_breakdowns_data)
        self.layout.addWidget(refresh_btn)

    def load_breakdowns_data(self):
        self.load_items_combo()
        self.load_repairer_combo()
        self.load_breakdowns()

    def load_data(self):
        self.load_breakdowns_data()

    def load_items_combo(self):
        try:
            response = APIClient.get("/items")
            items = response.json()
            self.breakdown_item_combo.clear()
            for item in items:
                self.breakdown_item_combo.addItem(item["name"], item["id"])
        except:
            pass

    def load_repairer_combo(self):
        current = self.breakdown_repairer_combo.currentData()
        try:
            response = APIClient.get("/users")
            users = response.json()
            self.breakdown_repairer_combo.blockSignals(True)
            self.breakdown_repairer_combo.clear()
            self.breakdown_repairer_combo.addItem("Нет", None)
            for user in users:
                fio = f"{user['surname']} {user['name']}"
                self.breakdown_repairer_combo.addItem(fio, user["id"])
            if current is not None:
                index = self.breakdown_repairer_combo.findData(current)
                if index >= 0:
                    self.breakdown_repairer_combo.setCurrentIndex(index)
            self.breakdown_repairer_combo.blockSignals(False)
        except:
            pass

    def refresh_combos(self):
        """Items and users may have been added in other tabs."""
        self.load_items_combo()
        self.load_repairer_combo()

    def report_breakdown(self):
        item_id = self.breakdown_item_combo.currentData()
        comment = self.breakdown_comment_input.text().strip()

        if not item_id or not comment:
            QMessageBox.warning(self, "Ошибка", "Заполните обязательные поля")
            return

        try:
            data = {
                "item_id": item_id,
                "comment": comment,
                "date": QDate.currentDate().toString("yyyy-MM-dd"),
                "repairer_id": self.breakdown_repairer_combo.currentData(),
            }

            response = APIClient.post(f"/breakdowns", data)
            if response.status_code == 201:
                QMessageBox.information(self, "Успех", "Поломка зарегистрирована")
                self.breakdown_comment_input.clear()
                self.load_breakdowns()
            else:
                QMessageBox.warning(self, "Ошибка", response.json().get("detail", "Ошибка"))
        except Exception as e:
            QMessageBox.critical(self, "Ошибка подключения", str(e))

    def load_breakdowns(self):
        try:
            # One request per entity instead of one per table row
            item_names = self.fetch_lookup("/items", "id", lambda i: i["name"])
            user_names = self.fetch_lookup("/users", "id", lambda u: f"{u['surname']} {u['name']}")

            response = APIClient.get(f"/breakdowns")
            breakdowns = response.json()
            self.breakdowns_table.setRowCount(len(breakdowns))

            for row, breakdown in enumerate(breakdowns):
                self.breakdowns_table.setItem(row, 0, QTableWidgetItem(str(breakdown["id"])))
                self.breakdowns_table.setItem(
                    row, 1, QTableWidgetItem(item_names.get(breakdown["item_id"], "")))

                self.breakdowns_table.setItem(row, 2, QTableWidgetItem(breakdown.get("comment", "")))
                self.breakdowns_table.setItem(row, 3, QTableWidgetItem(breakdown.get("date", "")))
                self.breakdowns_table.setItem(row, 4, QTableWidgetItem(
                    breakdown.get("repaired_date", "") or "Не отремонтирована"))

                # Get repairer name
                repairer_name = user_names.get(breakdown.get("repairer_id"), "") \
                    if breakdown.get("repairer_id") else ""

                self.breakdowns_table.setItem(row, 5, QTableWidgetItem(repairer_name))

                # Mark as repaired button
                if not breakdown.get("repaired_date"):
                    repair_btn = QPushButton("Отремонтирована")
                    repair_btn.clicked.connect(lambda checked, b_id=breakdown["id"]: self.mark_repaired(b_id))
                    self.breakdowns_table.setCellWidget(row, 6, repair_btn)
        except Exception as e:
            QMessageBox.critical(self, "Ошибка подключения", str(e))

    def mark_repaired(self, breakdown_id):
        try:
            data = {
                "repaired_date": QDate.currentDate().toString("yyyy-MM-dd")
            }
            response = APIClient.put(f"/breakdowns/{breakdown_id}", data)
            if response.status_code == 200:
                QMessageBox.information(self, "Успех", "Предмет отмечен как отремонтированный")
                self.load_breakdowns()
            else:
                QMessageBox.warning(self, "Ошибка", "Ошибка при обновлении")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка подключения", str(e))