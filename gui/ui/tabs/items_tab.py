from PyQt6.QtWidgets import (
    QPushButton, QLabel, QLineEdit, QTableWidget, QTableWidgetItem, QMessageBox,
    QComboBox, QGroupBox, QFormLayout, QSpinBox, QCheckBox, QHeaderView
)
from PyQt6.QtGui import QDoubleValidator
from gui.api.client import APIClient
from . import BaseTab, ITEM_STATUSES, translate_status


class ItemsTab(BaseTab):
    def __init__(self):
        super().__init__()
        self._categories = []
        self._storages = []
        self.init_ui()

    def init_ui(self):
        form_group = self.create_form_group("Добавить снаряжение")
        form = form_group.layout()

        self.item_name_input = QLineEdit()
        self.item_name_input.setPlaceholderText("Название предмета")
        form.addRow("Название:", self.item_name_input)

        # An item belongs to a club; its category and storage must be
        # from the same club (the club can never change later).
        self.item_club_combo = QComboBox()
        self.item_club_combo.currentIndexChanged.connect(self.on_club_changed)
        form.addRow("Клуб:", self.item_club_combo)

        self.item_category_combo = QComboBox()
        # Dynamic property fields below are rebuilt when the category changes
        self.item_category_combo.currentIndexChanged.connect(self.load_category_fields)
        form.addRow("Категория:", self.item_category_combo)

        self.item_storage_combo = QComboBox()
        form.addRow("Склад:", self.item_storage_combo)

        self.item_serial_input = QLineEdit()
        self.item_serial_input.setPlaceholderText("Серийный номер (опционально)")
        form.addRow("Серийный номер:", self.item_serial_input)

        self.item_status_combo = QComboBox()
        for code in ITEM_STATUSES:
            self.item_status_combo.addItem(translate_status(code), code)
        form.addRow("Статус:", self.item_status_combo)

        # ---------- dynamic per-category property fields ----------
        self.item_params_group = QGroupBox("Свойства категории")
        self.item_params_form = QFormLayout(self.item_params_group)
        form.addRow(self.item_params_group)
        self._param_fields = []  # [(parameter, widget, kind)]

        add_item_btn = QPushButton("Добавить предмет")
        add_item_btn.clicked.connect(self.add_item)
        form.addRow(add_item_btn)

        self.layout.addWidget(form_group)

        # Table
        self.items_table = QTableWidget()
        self.items_table.setColumnCount(8)
        self.items_table.setHorizontalHeaderLabels(
            ["ID", "Название", "Клуб", "Категория", "Склад", "Статус", "Серийный", "Свойства"])
        self.items_table.horizontalHeader().setSectionResizeMode(
            7, QHeaderView.ResizeMode.Stretch)
        self.layout.addWidget(QLabel("Список снаряжения:"))
        self.layout.addWidget(self.items_table)

        refresh_btn = QPushButton("Обновить")
        refresh_btn.clicked.connect(self.load_items_data)
        self.layout.addWidget(refresh_btn)

    # ---------- loading ----------
    def load_items_data(self):
        self._reload_lookups()
        self.load_items()

    def load_data(self):
        self.load_items_data()

    def refresh_combos(self):
        """Categories, storages and clubs may have changed in other tabs."""
        self._reload_lookups()

    def _reload_lookups(self):
        try:
            self._categories = APIClient.get("/categories").json()
        except Exception:
            self._categories = []
        try:
            self._storages = APIClient.get("/storages").json()
        except Exception:
            self._storages = []
        self.load_clubs_combo()

    def load_clubs_combo(self):
        try:
            clubs = APIClient.get("/clubs").json()
        except Exception:
            return
        current = self.item_club_combo.currentData()
        self.item_club_combo.blockSignals(True)
        self.item_club_combo.clear()
        for club in clubs:
            self.item_club_combo.addItem(club["name"], club["id"])
        if current is not None:
            index = self.item_club_combo.findData(current)
            if index >= 0:
                self.item_club_combo.setCurrentIndex(index)
        self.item_club_combo.blockSignals(False)
        self.on_club_changed()

    def on_club_changed(self):
        """Show only categories and storages of the selected club."""
        club_id = self.item_club_combo.currentData()

        self.item_category_combo.blockSignals(True)
        self.item_category_combo.clear()
        for category in self._categories:
            if category.get("club_id") == club_id:
                self.item_category_combo.addItem(category["title"], category["id"])
        self.item_category_combo.blockSignals(False)

        current_storage = self.item_storage_combo.currentData()
        self.item_storage_combo.clear()
        for storage in self._storages:
            if storage.get("club_id") == club_id:
                self.item_storage_combo.addItem(storage["name"], storage["id"])
        if current_storage is not None:
            index = self.item_storage_combo.findData(current_storage)
            if index >= 0:
                self.item_storage_combo.setCurrentIndex(index)

        self.load_category_fields()

    # ---------- dynamic per-category fields ----------
    def load_category_fields(self):
        """Rebuild the property input rows from the category's parameter
        set (inherited ones included). A parameter with predefined value
        variants becomes a dropdown, otherwise the widget follows its type."""
        # clear old rows
        while self.item_params_form.rowCount():
            self.item_params_form.removeRow(0)
        self._param_fields = []

        category_id = self.item_category_combo.currentData()
        if category_id is None:
            self.item_params_group.setVisible(False)
            return

        try:
            response = APIClient.get(f"/categories/{category_id}/parameters")
            parameters = response.json()
        except Exception:
            self.item_params_group.setVisible(False)
            return

        for parameter in parameters:
            label = parameter["name"] + (" (от родителя)" if parameter.get("inherited") else "")
            values = []
            try:
                values = APIClient.get(f"/values/parameter/{parameter['id']}").json()
            except Exception:
                pass

            if values:
                # Predefined variants -> dropdown, save as value_id
                widget = QComboBox()
                for variant in values:
                    widget.addItem(str(variant["value"]), variant["id"])
                kind = "select"
            elif parameter["param_type"] == "bool":
                widget = QCheckBox("да")
                kind = "bool"
            elif parameter["param_type"] == "int":
                widget = QSpinBox()
                widget.setRange(-999999, 999999)
                widget.setSpecialValueText("—")
                kind = "int"
            elif parameter["param_type"] == "float":
                widget = QLineEdit()
                widget.setPlaceholderText("число, напр. 12.5")
                widget.setValidator(QDoubleValidator())
                kind = "float"
            else:  # 'str'
                widget = QLineEdit()
                kind = "str"

            self.item_params_form.addRow(label, widget)
            self._param_fields.append((parameter, widget, kind))

        self.item_params_group.setVisible(bool(self._param_fields))

    # ---------- create ----------
    def add_item(self):
        name = self.item_name_input.text().strip()
        category_id = self.item_category_combo.currentData()
        storage_id = self.item_storage_combo.currentData()
        serial = self.item_serial_input.text().strip()
        status = self.item_status_combo.currentData()

        if not all([name, category_id, storage_id]):
            QMessageBox.warning(self, "Ошибка", "Заполните обязательные поля (клуб, категория, склад)")
            return

        try:
            data = {
                "name": name,
                "category_id": category_id,
                "storage_id": storage_id,
                "status": status
            }
            if serial:
                data["serial_number"] = serial

            response = APIClient.post("/items", data)
            if response.status_code == 201:
                item = response.json()
                self.save_item_parameters(item["id"])
                QMessageBox.information(self, "Успех", "Снаряжение добавлено")
                self.item_name_input.clear()
                self.item_serial_input.clear()
                self.load_items()
            else:
                QMessageBox.warning(self, "Ошибка", response.json().get("detail", "Ошибка"))
        except Exception as e:
            QMessageBox.critical(self, "Ошибка подключения", str(e))

    def save_item_parameters(self, item_id: int):
        """Store the values entered in the dynamic property rows."""
        for parameter, widget, kind in self._param_fields:
            payload = {"item_id": item_id, "parameter_id": parameter["id"]}

            if kind == "select":
                payload["value_id"] = widget.currentData()
            elif kind == "bool":
                payload["custom_value"] = "true" if widget.isChecked() else "false"
            elif kind == "int":
                if widget.value() == widget.minimum():  # '—' = not filled
                    continue
                payload["custom_value"] = str(widget.value())
            elif kind == "float":
                text = widget.text().strip().replace(",", ".")
                if not text:
                    continue
                payload["custom_value"] = text
            else:  # str
                text = widget.text().strip()
                if not text:
                    continue
                payload["custom_value"] = text

            try:
                APIClient.post("/item-parameters", payload)
            except Exception:
                pass  # one bad property must not block the item itself

    def load_items(self):
        try:
            # One request per entity instead of one per table row
            club_names = self.fetch_lookup("/clubs", "id", lambda c: c["name"])
            cat_names = self.fetch_lookup("/categories", "id", lambda c: c["title"])
            stor_names = self.fetch_lookup("/storages", "id", lambda s: s["name"])
            param_names = self.fetch_lookup("/parameters", "id", lambda p: p["name"])
            value_texts = self.fetch_lookup("/values", "id", lambda v: v["value"])

            # Group all parameter values by item: one request for the whole table
            props_by_item = {}
            item_params = APIClient.get("/item-parameters").json()
            for ip in item_params:
                if ip.get("value_id") is not None:
                    text = value_texts.get(ip["value_id"], str(ip["value_id"]))
                else:
                    text = ip.get("custom_value") or ""
                if text == "true":
                    text = "да"
                elif text == "false":
                    text = "нет"
                name = param_names.get(ip["parameter_id"], "")
                props_by_item.setdefault(ip["item_id"], []).append(f"{name} - {text}")

            response = APIClient.get(f"/items")
            items = response.json()
            self.items_table.setRowCount(len(items))

            for row, item in enumerate(items):
                self.items_table.setItem(row, 0, QTableWidgetItem(str(item["id"])))
                self.items_table.setItem(row, 1, QTableWidgetItem(item["name"]))
                self.items_table.setItem(
                    row, 2, QTableWidgetItem(club_names.get(item.get("club_id"), "")))
                self.items_table.setItem(
                    row, 3, QTableWidgetItem(cat_names.get(item["category_id"], "")))
                self.items_table.setItem(
                    row, 4, QTableWidgetItem(stor_names.get(item["storage_id"], "")))
                self.items_table.setItem(
                    row, 5, QTableWidgetItem(translate_status(item.get("status", ""))))
                self.items_table.setItem(row, 6, QTableWidgetItem(item.get("serial_number", "")))
                self.items_table.setItem(
                    row, 7, QTableWidgetItem(", ".join(props_by_item.get(item["id"], []))))
        except Exception as e:
            QMessageBox.critical(self, "Ошибка подключения", str(e))
