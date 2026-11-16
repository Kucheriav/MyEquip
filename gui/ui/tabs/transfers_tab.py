from PyQt6.QtWidgets import (
    QPushButton, QLabel, QLineEdit, QTableWidget, QTableWidgetItem, QMessageBox, QComboBox
)
from PyQt6.QtCore import QDate
from gui.api.client import APIClient
from . import BaseTab


class TransfersTab(BaseTab):
    def __init__(self):
        super().__init__()
        self.init_ui()
        # self.load_transfers_data()

    def init_ui(self):
        form_group = self.create_form_group("Переместить снаряжение")
        form = form_group.layout()

        self.transfer_item_combo = QComboBox()
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

    def load_items_combo(self):
        try:
            response = APIClient.get("/items")
            items = response.json()
            self.transfer_item_combo.blockSignals(True)
            self.transfer_item_combo.clear()
            for item in items:
                self.transfer_item_combo.addItem(item["name"], item["id"])
            self.transfer_item_combo.blockSignals(False)
            self.on_item_selected()
        except:
            pass

    def on_item_selected(self):
        """Show the item's current storage as the (fixed) source."""
        item_id = self.transfer_item_combo.currentData()
        if not item_id:
            self.transfer_from_label.setText("—")
            return
        try:
            response = APIClient.get(f"/items/{item_id}")
            item = response.json()
            storage_id = item.get("storage_id")
            storage_name = ""
            if storage_id:
                storage_resp = APIClient.get(f"/storages/{storage_id}")
                storage_name = storage_resp.json().get("name", "")
            self.transfer_from_label.setText(f"{storage_name} (id {storage_id})")
        except:
            self.transfer_from_label.setText("—")

    def load_users_combo(self):
        try:
            response = APIClient.get("/users")
            users = response.json()
            self.transfer_mover_combo.clear()
            for user in users:
                fio = f"{user['surname']} {user['name']}"
                self.transfer_mover_combo.addItem(fio, user["id"])
        except:
            pass

    def load_storages_combo(self):
        try:
            response = APIClient.get("/storages")
            storages = response.json()
            current = self.transfer_to_combo.currentData()
            self.transfer_to_combo.clear()
            for storage in storages:
                self.transfer_to_combo.addItem(storage["name"], storage["id"])
            if current is not None:
                index = self.transfer_to_combo.findData(current)
                if index >= 0:
                    self.transfer_to_combo.setCurrentIndex(index)
        except:
            pass

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
            response = APIClient.get("/transfers")
            transfers = response.json()
            self.transfers_table.setRowCount(len(transfers))

            for row, transfer in enumerate(transfers):
                self.transfers_table.setItem(row, 0, QTableWidgetItem(str(transfer["id"])))

                item_name = ""
                try:
                    item_name = APIClient.get(f"/items/{transfer['item_id']}").json().get("name", "")
                except:
                    pass
                self.transfers_table.setItem(row, 1, QTableWidgetItem(item_name))

                from_name = to_name = ""
                try:
                    from_name = APIClient.get(f"/storages/{transfer['from_storage_id']}").json().get("name", "")
                    to_name = APIClient.get(f"/storages/{transfer['to_storage_id']}").json().get("name", "")
                except:
                    pass
                self.transfers_table.setItem(row, 2, QTableWidgetItem(from_name))
                self.transfers_table.setItem(row, 3, QTableWidgetItem(to_name))

                self.transfers_table.setItem(row, 4, QTableWidgetItem(transfer.get("date", "")))
                self.transfers_table.setItem(row, 5, QTableWidgetItem(transfer.get("comment") or ""))
        except Exception as e:
            QMessageBox.critical(self, "Ошибка подключения", str(e))
