from PyQt6.QtWidgets import (
    QPushButton, QLabel, QLineEdit, QTableWidget, QTableWidgetItem, QMessageBox,
    QComboBox, QDateEdit, QDialog, QDialogButtonBox, QFormLayout, QVBoxLayout
)
from PyQt6.QtCore import QDate
from gui.api.client import APIClient
from . import (
    BaseTab, translate_status, users_of_club, fill_user_combo, current_user_id
)


class ReturnDialog(QDialog):
    """Accepting an issued item back.

    A returned item goes into a storage of its club — by default the one
    it came from, but the accepter may choose another one. The accepter
    is always the logged-in user.
    """

    def __init__(self, parent, item: dict, storages: list):
        super().__init__(parent)
        self.setWindowTitle("Приёмка снаряжения")
        self.resize(420, 230)

        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.item_label = QLabel(item.get("name", ""))
        form.addRow("Предмет:", self.item_label)

        self.storage_combo = QComboBox()
        for storage in storages:
            self.storage_combo.addItem(storage["name"], storage["id"])
        # Preselect the item's current storage
        index = self.storage_combo.findData(item.get("storage_id"))
        if index >= 0:
            self.storage_combo.setCurrentIndex(index)
        form.addRow("Склад:", self.storage_combo)

        self.date_edit = QDateEdit()
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDate(QDate.currentDate())
        form.addRow("Дата приёмки:", self.date_edit)

        self.comment_input = QLineEdit()
        self.comment_input.setPlaceholderText("Комментарий (опционально)")
        form.addRow("Комментарий:", self.comment_input)

        layout.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Принять")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("Отмена")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def payload(self) -> dict:
        data = {
            "accepting_date": self.date_edit.date().toString("yyyy-MM-dd"),
            "storage_id": self.storage_combo.currentData(),
        }
        accepter_id = current_user_id()
        if accepter_id is not None:
            data["accepter_id"] = accepter_id
        comment = self.comment_input.text().strip()
        if comment:
            data["comment"] = comment
        return data


class DistributionsTab(BaseTab):
    def __init__(self):
        super().__init__()
        self._items_by_id = {}
        self._users = []
        self.init_ui()

    def init_ui(self):
        form_group = self.create_form_group("Выдать снаряжение")
        form = form_group.layout()

        self.dist_item_combo = QComboBox()
        self.dist_item_combo.currentIndexChanged.connect(self.on_item_changed)
        form.addRow("Предмет:", self.dist_item_combo)

        # The giver is always the logged-in user; anybody in the club can
        # receive the equipment (tourists included).
        self.dist_getter_combo = QComboBox()
        form.addRow("Получающий:", self.dist_getter_combo)

        self.dist_expiration_date = QDateEdit()
        self.dist_expiration_date.setCalendarPopup(True)
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
        self.distributions_table.setColumnCount(9)
        self.distributions_table.setHorizontalHeaderLabels(
            ["ID", "Предмет", "Выдавший", "Получивший", "Дата выдачи",
             "Возврат до", "Склад", "Статус", "Действия"]
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
            items = APIClient.get("/items").json()
            self._items_by_id = {item["id"]: item for item in items}
            current = self.dist_item_combo.currentData()
            self.dist_item_combo.blockSignals(True)
            self.dist_item_combo.clear()
            for item in items:
                self.dist_item_combo.addItem(item["name"], item["id"])
            if current is not None:
                index = self.dist_item_combo.findData(current)
                if index >= 0:
                    self.dist_item_combo.setCurrentIndex(index)
            self.dist_item_combo.blockSignals(False)
            self.on_item_changed()
        except Exception:
            pass

    def load_users_combo(self):
        try:
            self._users = APIClient.get("/users").json()
            self.on_item_changed()
        except Exception:
            pass

    def on_item_changed(self):
        """Offer only the members of the item's club as getters."""
        item = self._items_by_id.get(self.dist_item_combo.currentData())
        club_id = item.get("club_id") if item else None
        fill_user_combo(
            self.dist_getter_combo,
            users_of_club(self._users, club_id),
            keep_current=False,
        )

    def load_data(self):
        self.load_distributions_data()

    def refresh_combos(self):
        """Items and users may have been added in other tabs."""
        self.load_items_combo()
        self.load_users_combo()

    def issue_item(self):
        item_id = self.dist_item_combo.currentData()
        getter_id = self.dist_getter_combo.currentData()
        expiration_date = self.dist_expiration_date.date().toString("yyyy-MM-dd")
        comment = self.dist_comment_input.text().strip()

        if not all([item_id, getter_id]):
            QMessageBox.warning(self, "Ошибка", "Выберите предмет и получающего.")
            return

        # The issuer is always the logged-in user
        giver_id = current_user_id()
        if giver_id is None:
            QMessageBox.warning(
                self, "Ошибка",
                "Не удалось определить текущего пользователя.\n"
                "Войдите в систему заново.")
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
            # One request per entity instead of one per table row
            items = APIClient.get("/items").json()
            self._items_by_id = {item["id"]: item for item in items}
            item_names = {item["id"]: item["name"] for item in items}
            storage_names = self.fetch_lookup("/storages", "id", lambda s: s["name"])
            user_names = self.fetch_lookup("/users", "id", lambda u: f"{u['surname']} {u['name']}")

            response = APIClient.get("/distributions")
            distributions = response.json()
            self.distributions_table.setRowCount(len(distributions))

            for row, dist in enumerate(distributions):
                item = self._items_by_id.get(dist["item_id"], {})
                self.distributions_table.setItem(row, 0, QTableWidgetItem(str(dist["id"])))
                self.distributions_table.setItem(
                    row, 1, QTableWidgetItem(item_names.get(dist["item_id"], "")))
                self.distributions_table.setItem(
                    row, 2, QTableWidgetItem(user_names.get(dist["giver_id"], "")))
                self.distributions_table.setItem(
                    row, 3, QTableWidgetItem(user_names.get(dist["getter_id"], "")))

                self.distributions_table.setItem(row, 4, QTableWidgetItem(dist.get("date", "")))
                self.distributions_table.setItem(row, 5, QTableWidgetItem(dist.get("expiration_date", "")))
                self.distributions_table.setItem(
                    row, 6, QTableWidgetItem(storage_names.get(item.get("storage_id"), "")))
                self.distributions_table.setItem(
                    row, 7, QTableWidgetItem(translate_status(dist.get("status", ""))))

                # Return button: only while the item is actually out
                if dist.get("status") != "returned":
                    return_btn = QPushButton("Принять")
                    return_btn.clicked.connect(
                        lambda checked, d_id=dist["id"]: self.return_item(d_id))
                    self.distributions_table.setCellWidget(row, 8, return_btn)
                else:
                    self.distributions_table.setItem(
                        row, 8, QTableWidgetItem(dist.get("accepting_date") or ""))
        except Exception as e:
            QMessageBox.critical(self, "Ошибка подключения", str(e))

    def return_item(self, distribution_id):
        """Accept the item back, optionally into another storage."""
        try:
            response = APIClient.get(f"/distributions/{distribution_id}")
            if response.status_code != 200:
                QMessageBox.warning(self, "Ошибка", response.json().get("detail", "Ошибка"))
                return
            distribution = response.json()

            item = self._items_by_id.get(distribution["item_id"])
            if item is None:
                item_response = APIClient.get(f"/items/{distribution['item_id']}")
                if item_response.status_code != 200:
                    QMessageBox.warning(self, "Ошибка", "Предмет не найден")
                    return
                item = item_response.json()

            club_id = item.get("club_id")
            storages = [
                s for s in APIClient.get("/storages").json()
                if s.get("club_id") == club_id
            ]

            dialog = ReturnDialog(self, item, storages)
            if dialog.exec() != QDialog.DialogCode.Accepted:
                return

            result = APIClient.post(
                f"/distributions/{distribution_id}/return", dialog.payload())
            if result.status_code == 200:
                QMessageBox.information(self, "Успех", "Снаряжение принято")
                self.load_distributions()
            else:
                QMessageBox.warning(self, "Ошибка", result.json().get("detail", "Ошибка"))
        except Exception as e:
            QMessageBox.critical(self, "Ошибка подключения", str(e))
