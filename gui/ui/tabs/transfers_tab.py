from PyQt6.QtWidgets import (
    QPushButton, QLabel, QLineEdit, QTableWidget, QTableWidgetItem, QMessageBox, QComboBox
)
from PyQt6.QtCore import QDate
from gui.api.client import APIClient
from . import BaseTab, users_of_club, fill_user_combo


class TransfersTab(BaseTab):
    def __init__(self):
        super().__init__()
        self._items_by_id = {}
        self._users = []
        self._storages = []
        self.init_ui()

    def init_ui(self):
        form_group = self.create_form_group("Переместить снаряжение")
        form = form_group.layout()

        self.transfer_item_combo = QComboBox()
        self.transfer_item_combo.currentIndexChanged.connect(self.on_item_selected)
        form.addRow("Предмет:", self.transfer_item_combo)

        self.transfer_from_label = QLabel("—")
        form.addRow("Со склада:", self.transfer_from_label)

        self.transfer_to_combo = QComboBox()
        form.addRow("На склад:", self.transfer_to_combo)

        self.transfer_mover_combo = QComboBox()
        form.addRow("Передающий:", self.transfer_mover_combo)

        self.transfer_comment_input = QLineEdit()
        self.transfer_comment_input.setPlaceholderText("Комментарий (опционально)")
        form.addRow("Комментарий:", self.transfer_comment_input)

        transfer_btn = QPushButton("Переместить")
        transfer_btn.clicked.connect(self.make_transfer)
        form.addRow(transfer_btn)

        self.layout.addWidget(form_group)

        # Table
        self.transfers_table = QTableWidget()
        self.transfers_table.setColumnCount(6)
        self.transfers_table.setHorizontalHeaderLabels(
            ["ID", "Предмет", "Откуда", "Куда", "Дата", "Комментарий"]
        )
        self.layout.addWidget(QLabel("История перемещений:"))
        self.layout.addWidget(self.transfers_table)

        refresh_btn = QPushButton("Обновить")
        refresh_btn.clicked.connect(self.load_transfers_data)
        self.layout.addWidget(refresh_btn)

    def load_transfers_data(self):
        self.load_items_combo()
        self.load_users_combo()
        self.load_storages_combo()
        self.load_transfers()

    def refresh_combos(self):
        """Items, users and storages may have been added in other tabs."""
        self.load_items_combo()
        self.load_users_combo()
        self.load_storages_combo()

    def load_data(self):
        self.load_transfers_data()

    def load_items_combo(self):
        try:
            items = APIClient.get("/items").json()
            self._items_by_id = {item["id"]: item for item in items}
            current = self.transfer_item_combo.currentData()
            self.transfer_item_combo.blockSignals(True)
            self.transfer_item_combo.clear()
            for item in items:
                self.transfer_item_combo.addItem(item["name"], item["id"])
            if current is not None:
                index = self.transfer_item_combo.findData(current)
                if index >= 0:
                    self.transfer_item_combo.setCurrentIndex(index)
            self.transfer_item_combo.blockSignals(False)
            self.on_item_selected()
        except Exception:
            pass

    def load_users_combo(self):
        try:
            self._users = APIClient.get("/users").json()
            self.on_item_selected()
        except Exception:
            pass

    def load_storages_combo(self):
        try:
            self._storages = APIClient.get("/storages").json()
            self.on_item_selected()
        except Exception:
            pass

    def on_item_selected(self):
        """Show the item's current storage as the (fixed) source and offer
        only storages of the same club; the mover is club staff."""
        item = self._items_by_id.get(self.transfer_item_combo.currentData())
        if not item:
            self.transfer_from_label.setText("—")
            self.transfer_to_combo.clear()
            self.transfer_mover_combo.clear()
            return

        club_id = item.get("club_id")
        storage_id = item.get("storage_id")
        storage_names = {s["id"]: s["name"] for s in self._storages}
        self.transfer_from_label.setText(
            f"{storage_names.get(storage_id, '')} (id {storage_id})")

        # Destination: other storages of the item's own club
        current = self.transfer_to_combo.currentData()
        self.transfer_to_combo.blockSignals(True)
        self.transfer_to_combo.clear()
        for storage in self._storages:
            if storage.get("club_id") == club_id and storage["id"] != storage_id:
                self.transfer_to_combo.addItem(storage["name"], storage["id"])
        index = self.transfer_to_combo.findData(current)
        if index >= 0:
            self.transfer_to_combo.setCurrentIndex(index)
        self.transfer_to_combo.blockSignals(False)

        fill_user_combo(
            self.transfer_mover_combo,
            users_of_club(self._users, club_id, staff_only=True),
            keep_current=False,
        )

    def make_transfer(self):
        item_id = self.transfer_item_combo.currentData()
        mover_id = self.transfer_mover_combo.currentData()
        to_storage_id = self.transfer_to_combo.currentData()
        comment = self.transfer_comment_input.text().strip()

        if not all([item_id, to_storage_id]):
            QMessageBox.warning(self, "Ошибка", "Выберите предмет и склад назначения")
            return

        # Source storage is taken from the item itself
        try:
            item = APIClient.get(f"/items/{item_id}").json()
            from_storage_id = item.get("storage_id")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка подключения", str(e))
            return

        if not from_storage_id:
            QMessageBox.warning(self, "Ошибка", "Не удалось определить текущий склад предмета")
            return

        try:
            data = {
                "item_id": item_id,
                "from_storage_id": from_storage_id,
                "to_storage_id": to_storage_id,
                "date": QDate.currentDate().toString("yyyy-MM-dd"),
            }
            if mover_id:
                data["mover_id"] = mover_id
            if comment:
                data["comment"] = comment

            response = APIClient.post("/transfers", data)
            if response.status_code == 201:
                QMessageBox.information(self, "Успех", "Предмет перемещён")
                self.transfer_comment_input.clear()
                self.load_transfers()
            else:
                QMessageBox.warning(self, "Ошибка", response.json().get("detail", "Ошибка"))
        except Exception as e:
            QMessageBox.critical(self, "Ошибка подключения", str(e))

    def load_transfers(self):
        try:
            # One request per entity instead of one per table row
            item_names = self.fetch_lookup("/items", "id", lambda i: i["name"])
            stor_names = self.fetch_lookup("/storages", "id", lambda s: s["name"])

            response = APIClient.get("/transfers")
            transfers = response.json()
            self.transfers_table.setRowCount(len(transfers))

            for row, transfer in enumerate(transfers):
                self.transfers_table.setItem(row, 0, QTableWidgetItem(str(transfer["id"])))
                self.transfers_table.setItem(
                    row, 1, QTableWidgetItem(item_names.get(transfer["item_id"], "")))
                self.transfers_table.setItem(
                    row, 2, QTableWidgetItem(stor_names.get(transfer["from_storage_id"], "")))
                self.transfers_table.setItem(
                    row, 3, QTableWidgetItem(stor_names.get(transfer["to_storage_id"], "")))

                self.transfers_table.setItem(row, 4, QTableWidgetItem(transfer.get("date", "")))
                self.transfers_table.setItem(row, 5, QTableWidgetItem(transfer.get("comment") or ""))
        except Exception as e:
            QMessageBox.critical(self, "Ошибка подключения", str(e))
