from PyQt6.QtWidgets import (
    QPushButton, QLabel, QLineEdit, QTableWidget, QTableWidgetItem, QMessageBox, QComboBox, QDateEdit
)
from PyQt6.QtCore import QDate
from gui.api.client import APIClient
from . import BaseTab


class DistributionsTab(BaseTab):
    def __init__(self):
        super().__init__()
        self.init_ui()
        self.load_distributions_data()

    def init_ui(self):
        form_group = self.create_form_group("Выдать снаряжение")
        form = form_group.layout()

        self.dist_item_combo = QComboBox()
        form.addRow("Предмет:", self.dist_item_combo)

        self.dist_giver_combo = QComboBox()
        form.addRow("Выдающий:", self.dist_giver_combo)

        self.dist_getter_combo = QComboBox()
        form.addRow("Получающий:", self.dist_getter_combo)

        self.dist_expiration_date = QDateEdit()
        self.dist_expiration_date.setDate(QDate.currentDate())
        form.addRow("Дата возврата:", self.dist_expiration_date)

        self.dist_comment_input = QLineEdit()
        self.dist_comment_input.setPlaceholderText("Комментарий (опционально)")
        form.addRow("Комментарий:", self.dist_comment_input)

        issue_btn = QPushButton("Выдать предмет")
        issue_btn.clicked.connect(self.issue_item)
        form.addRow(issue_btn)

        self.layout.addWidget(form_group)

        # Table
        self.distributions_table = QTableWidget()
        self.distributions_table.setColumnCount(8)
        self.distributions_table.setHorizontalHeaderLabels(
            ["ID", "Предмет", "Выдавший", "Получивший", "Дата выдачи", "Возврат до", "Статус", "Действия"]
        )
        self.layout.addWidget(QLabel("История выдачи:"))
        self.layout.addWidget(self.distributions_table)

        refresh_btn = QPushButton("Обновить")
        refresh_btn.clicked.connect(self.load_distributions_data)
        self.layout.addWidget(refresh_btn)

    def load_distributions_data(self):
        self.load_items_combo()
        self.load_users_combo()
        self.load_distributions()

    def load_items_combo(self):
        try:
            response = APIClient.get(f"/items")
            items = response.json()
            self.dist_item_combo.clear()
            for item in items:
                self.dist_item_combo.addItem(item["name"], item["id"])
        except:
            pass

    def load_users_combo(self):
        try:
            response = APIClient.get("/users")
            users = response.json()
            self.dist_giver_combo.clear()
            self.dist_getter_combo.clear()
            for user in users:
                fio = f"{user['surname']} {user['name']}"
                self.dist_giver_combo.addItem(fio, user["id"])
                self.dist_getter_combo.addItem(fio, user["id"])
        except:
            pass

    def refresh_combos(self):
        """Items and users may have been added in other tabs."""
        self.load_items_combo()
        self.load_users_combo()

    def issue_item(self):
        item_id = self.dist_item_combo.currentData()
        giver_id = self.dist_giver_combo.currentData()
        getter_id = self.dist_getter_combo.currentData()
        expiration_date = self.dist_expiration_date.date().toString("yyyy-MM-dd")
        comment = self.dist_comment_input.text().strip()

        if not all([item_id, giver_id, getter_id]):
            QMessageBox.warning(self, "Ошибка", "Выберите предмет, выдающего и получающего")
            return

        try:
            data = {
                "item_id": item_id,
                "giver_id": giver_id,
                "getter_id": getter_id,
                "date": QDate.currentDate().toString("yyyy-MM-dd"),
                "expiration_date": expiration_date,
                "status": "issued"
            }
            if comment:
                data["comment"] = comment

            response = APIClient.post("/distributions", data)
            if response.status_code == 201:
                QMessageBox.information(self, "Успех", "Снаряжение выдано")
                self.dist_comment_input.clear()
                self.load_distributions()
            else:
                QMessageBox.warning(self, "Ошибка", response.json().get("detail", "Ошибка"))
        except Exception as e:
            QMessageBox.critical(self, "Ошибка подключения", str(e))

    def load_distributions(self):
        try:
            response = APIClient.get("/distributions")
            distributions = response.json()
            self.distributions_table.setRowCount(len(distributions))

            for row, dist in enumerate(distributions):
                self.distributions_table.setItem(row, 0, QTableWidgetItem(str(dist["id"])))

                # Get item name
                try:
                    item_resp = APIClient.get(f"/items/{dist['item_id']}")
                    item_name = item_resp.json().get("name", "")
                    self.distributions_table.setItem(row, 1, QTableWidgetItem(item_name))
                except:
                    self.distributions_table.setItem(row, 1, QTableWidgetItem(""))

                # Get giver name
                try:
                    giver_resp = APIClient.get(f"/users/{dist['giver_id']}")
                    giver_data = giver_resp.json()
                    giver_name = f"{giver_data['surname']} {giver_data['name']}"
                    self.distributions_table.setItem(row, 2, QTableWidgetItem(giver_name))
                except:
                    self.distributions_table.setItem(row, 2, QTableWidgetItem(""))

                # Get getter name
                try:
                    getter_resp = APIClient.get(f"/users/{dist['getter_id']}")
                    getter_data = getter_resp.json()
                    getter_name = f"{getter_data['surname']} {getter_data['name']}"
                    self.distributions_table.setItem(row, 3, QTableWidgetItem(getter_name))
                except:
                    self.distributions_table.setItem(row, 3, QTableWidgetItem(""))

                self.distributions_table.setItem(row, 4, QTableWidgetItem(dist.get("date", "")))
                self.distributions_table.setItem(row, 5, QTableWidgetItem(dist.get("expiration_date", "")))
                self.distributions_table.setItem(row, 6, QTableWidgetItem(dist.get("status", "")))

                # Return button
                return_btn = QPushButton("Вернуть")
                return_btn.clicked.connect(lambda checked, d_id=dist["id"]: self.return_item(d_id))
                self.distributions_table.setCellWidget(row, 7, return_btn)
        except Exception as e:
            QMessageBox.critical(self, "Ошибка подключения", str(e))

    def return_item(self, distribution_id):
        try:
            data = {
                "status": "returned",
                "accepting_date": QDate.currentDate().toString("yyyy-MM-dd")
            }
            response = APIClient.put(f"/distributions/{distribution_id}", data)
            if response.status_code == 200:
                QMessageBox.information(self, "Успех", "Предмет отмечен как возвращенный")
                self.load_distributions()
            else:
                QMessageBox.warning(self, "Ошибка", "Ошибка при возврате")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка подключения", str(e))