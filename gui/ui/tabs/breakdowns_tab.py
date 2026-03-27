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
        # self.load_breakdowns_data()

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
        self.load_breakdowns()

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
                "date": QDate.currentDate().toString("yyyy-MM-dd")
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
            response = APIClient.get(f"/breakdowns")
            breakdowns = response.json()
            self.breakdowns_table.setRowCount(len(breakdowns))

            for row, breakdown in enumerate(breakdowns):
                self.breakdowns_table.setItem(row, 0, QTableWidgetItem(str(breakdown["id"])))

                # Get item name
                try:
                    item_resp = APIClient.get(f"/items/{breakdown['item_id']}")
                    item_name = item_resp.json().get("name", "")
                    self.breakdowns_table.setItem(row, 1, QTableWidgetItem(item_name))
                except:
                    self.breakdowns_table.setItem(row, 1, QTableWidgetItem(""))

                self.breakdowns_table.setItem(row, 2, QTableWidgetItem(breakdown.get("comment", "")))
                self.breakdowns_table.setItem(row, 3, QTableWidgetItem(breakdown.get("date", "")))
                self.breakdowns_table.setItem(row, 4, QTableWidgetItem(
                    breakdown.get("repaired_date", "") or "Не отремонтирована"))

                # Get repairer name
                repairer_name = ""
                if breakdown.get("repairer_id"):
                    try:
                        repairer_resp = APIClient.get(f"/users/{breakdown['repairer_id']}")
                        repairer_data = repairer_resp.json()
                        repairer_name = f"{repairer_data['surname']} {repairer_data['name']}"
                    except:
                        pass

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