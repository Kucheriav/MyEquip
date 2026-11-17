from PyQt6.QtWidgets import (
    QPushButton, QLabel, QLineEdit, QTableWidget, QTableWidgetItem,
    QMessageBox, QComboBox, QGroupBox, QFormLayout, QVBoxLayout,
    QHeaderView, QAbstractItemView
)
from gui.api.client import APIClient
from . import BaseTab

# Human-readable type names <-> API param_type values
TYPE_LABELS = [
    ("Число", "int"),
    ("Число дробное", "float"),
    ("Текст", "str"),
    ("Да/Нет", "bool"),
]
TYPE_API_TO_LABEL = {api: label for label, api in TYPE_LABELS}


class CategoriesTab(BaseTab):
    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        # ---------- add category form ----------
        form_group = self.create_form_group("Добавить категорию")
        form = form_group.layout()

        self.category_title_input = QLineEdit()
        self.category_title_input.setPlaceholderText("Название категории")
        form.addRow("Название:", self.category_title_input)

        self.category_club_combo = QComboBox()
        form.addRow("Клуб:", self.category_club_combo)

        self.category_parent_combo = QComboBox()
        self.category_parent_combo.addItem("Нет", None)
        form.addRow("Родительская категория:", self.category_parent_combo)

        add_category_btn = QPushButton("Добавить категорию")
        add_category_btn.clicked.connect(self.add_category)
        form.addRow(add_category_btn)

        self.layout.addWidget(form_group)

        # ---------- categories table ----------
        self.categories_table = QTableWidget()
        self.categories_table.setColumnCount(4)
        self.categories_table.setHorizontalHeaderLabels(["ID", "Название", "Клуб", "Родитель"])
        self.categories_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.layout.addWidget(QLabel("Список категорий:"))
        self.layout.addWidget(self.categories_table)

        refresh_btn = QPushButton("Обновить")
        refresh_btn.clicked.connect(self.load_categories)
        self.layout.addWidget(refresh_btn)

        # ---------- category properties panel ----------
        props_group = QGroupBox("Свойства категории (характеристики снаряжения этого типа)")
        props_layout = QVBoxLayout(props_group)

        self.param_category_combo = QComboBox()
        self.param_category_combo.currentIndexChanged.connect(self.load_category_parameters)
        props_layout.addWidget(QLabel("Категория:"))
        props_layout.addWidget(self.param_category_combo)

        self.params_table = QTableWidget()
        self.params_table.setColumnCount(3)
        self.params_table.setHorizontalHeaderLabels(["Свойство", "Тип", "Источник"])
        self.params_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.params_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        props_layout.addWidget(self.params_table)

        detach_btn = QPushButton("Отвязать выбранное свойство")
        detach_btn.clicked.connect(self.detach_selected_parameter)
        props_layout.addWidget(detach_btn)

        # add / attach property form
        prop_form = QFormLayout()
        self.param_name_input = QLineEdit()
        self.param_name_input.setPlaceholderText("Например: Температура комфорта")
        prop_form.addRow("Свойство:", self.param_name_input)

        self.param_type_combo = QComboBox()
        for label, _api in TYPE_LABELS:
            self.param_type_combo.addItem(label)
        prop_form.addRow("Тип:", self.param_type_combo)

        self.param_values_input = QLineEdit()
        self.param_values_input.setPlaceholderText(
            "Необязательно: варианты через запятую, напр. 2, 3, 4\n"
            "(заполнять имеет смысл только для текста или чисел)")
        prop_form.addRow("Варианты:", self.param_values_input)

        attach_btn = QPushButton("Добавить свойство к категории")
        attach_btn.clicked.connect(self.add_category_parameter)
        prop_form.addRow(attach_btn)

        props_layout.addLayout(prop_form)
        self.layout.addWidget(props_group)

    # ---------- helpers ----------
    def _selected_category_id(self):
        cat_id = self.param_category_combo.currentData()
        if cat_id is None and self.categories_table.currentRow() >= 0:
            item = self.categories_table.item(self.categories_table.currentRow(), 0)
            if item:
                cat_id = int(item.text())
        return cat_id

    # ---------- base tab API ----------
    def load_clubs_combo(self):
        try:
            response = APIClient.get("/clubs")
            clubs = response.json()
            self.category_club_combo.clear()
            for club in clubs:
                self.category_club_combo.addItem(club["name"], club["id"])
        except:
            pass

    def refresh_combos(self):
        """A club may have been added in the Clubs tab since last visit."""
        self.load_clubs_combo()

    def load_data(self):
        self.load_clubs_combo()
        self.load_categories()

    # ---------- categories ----------
    def add_category(self):
        title = self.category_title_input.text().strip()
        club_id = self.category_club_combo.currentData()
        parent_id = self.category_parent_combo.currentData()

        if not title or not club_id:
            QMessageBox.warning(self, "Ошибка", "Заполните обязательные поля")
            return

        try:
            data = {"title": title, "club_id": club_id}
            if parent_id:
                data["parent_id"] = parent_id

            response = APIClient.post("/categories", data)
            if response.status_code == 201:
                QMessageBox.information(self, "Успех", "Категория добавлена")
                self.category_title_input.clear()
                self.load_categories()
            else:
                QMessageBox.warning(self, "Ошибка", response.json().get("detail", "Ошибка"))
        except Exception as e:
            QMessageBox.critical(self, "Ошибка подключения", str(e))

    def load_categories(self):
        try:
            response = APIClient.get("/categories")
            categories = response.json()
            self.categories_table.setRowCount(len(categories))

            # One request for clubs instead of one per table row
            club_names = self.fetch_lookup("/clubs", "id", lambda c: c["name"])
            # Parent names come from the same list we already have
            parent_names = {c["id"]: c["title"] for c in categories}

            # Reload parent combo and the properties-panel category combo
            previous = self.param_category_combo.currentData()
            self.category_parent_combo.clear()
            self.category_parent_combo.addItem("Нет", None)
            self.param_category_combo.blockSignals(True)
            self.param_category_combo.clear()

            for row, category in enumerate(categories):
                self.categories_table.setItem(row, 0, QTableWidgetItem(str(category["id"])))
                self.categories_table.setItem(row, 1, QTableWidgetItem(category["title"]))
                self.categories_table.setItem(
                    row, 2, QTableWidgetItem(club_names.get(category["club_id"], "")))

                parent_name = parent_names.get(category.get("parent_id"), "") \
                    if category.get("parent_id") else ""

                self.categories_table.setItem(row, 3, QTableWidgetItem(parent_name))
                self.category_parent_combo.addItem(category["title"], category["id"])
                self.param_category_combo.addItem(
                    f"{category['title']} (id {category['id']})", category["id"])

            if previous is not None:
                index = self.param_category_combo.findData(previous)
                if index >= 0:
                    self.param_category_combo.setCurrentIndex(index)
            self.param_category_combo.blockSignals(False)
            self.load_category_parameters()
        except Exception as e:
            QMessageBox.critical(self, "Ошибка подключения", str(e))

    # ---------- category parameters ----------
    def load_category_parameters(self):
        """Show the effective parameter set of the selected category."""
        category_id = self.param_category_combo.currentData()
        self.params_table.setRowCount(0)
        if category_id is None:
            return
        try:
            response = APIClient.get(f"/categories/{category_id}/parameters")
            parameters = response.json()
            self.params_table.setRowCount(len(parameters))
            for row, parameter in enumerate(parameters):
                self.params_table.setItem(
                    row, 0, QTableWidgetItem(parameter["name"]))
                self.params_table.setItem(
                    row, 1, QTableWidgetItem(TYPE_API_TO_LABEL.get(parameter["param_type"], parameter["param_type"])))
                self.params_table.setItem(
                    row, 2, QTableWidgetItem("от родителя" if parameter.get("inherited") else "своё"))
        except Exception as e:
            QMessageBox.critical(self, "Ошибка подключения", str(e))

    def add_category_parameter(self):
        """Create a new property (or reuse one with the same name) and
        attach it to the selected category. Optional predefined values
        are stored as the parameter's Value list."""
        category_id = self.param_category_combo.currentData()
        name = self.param_name_input.text().strip()
        param_type = TYPE_LABELS[self.param_type_combo.currentIndex()][1]
        variants = [v.strip() for v in self.param_values_input.text().split(",") if v.strip()]

        if not category_id:
            QMessageBox.warning(self, "Ошибка", "Выберите категорию")
            return
        if not name:
            QMessageBox.warning(self, "Ошибка", "Введите название свойства")
            return

        try:
            # Reuse an existing parameter with the same name, create otherwise
            existing = APIClient.get("/parameters").json()
            parameter = next((p for p in existing if p["name"].lower() == name.lower()), None)

            if parameter is None:
                created = APIClient.post("/parameters", {"name": name, "param_type": param_type})
                if created.status_code != 201:
                    QMessageBox.warning(self, "Ошибка", created.json().get("detail", "Ошибка"))
                    return
                parameter = created.json()

                # Predefined value options -> Value list (shown as a dropdown later)
                for variant in variants:
                    APIClient.post("/values", {"value": variant, "parameter_id": parameter["id"]})

            attach = APIClient.post(f"/categories/{category_id}/parameters",
                                    {"parameter_id": parameter["id"]})
            if attach.status_code != 201 and attach.status_code != 200:
                QMessageBox.warning(self, "Ошибка", attach.json().get("detail", "Ошибка"))
                return

            self.param_name_input.clear()
            self.param_values_input.clear()
            self.load_category_parameters()
        except Exception as e:
            QMessageBox.critical(self, "Ошибка подключения", str(e))

    def detach_selected_parameter(self):
        category_id = self.param_category_combo.currentData()
        row = self.params_table.currentRow()
        if category_id is None or row < 0:
            QMessageBox.warning(self, "Ошибка", "Выберите категорию и свойство в списке")
            return
        name_item = self.params_table.item(row, 0)
        source_item = self.params_table.item(row, 2)
        if name_item is None:
            return
        if source_item and source_item.text() == "от родителя":
            QMessageBox.warning(
                self, "Ошибка",
                "Это свойство унаследовано от родительской категории — отвяжите его там.")
            return

        try:
            parameters = APIClient.get("/parameters").json()
            parameter = next((p for p in parameters if p["name"] == name_item.text()), None)
            if parameter is None:
                return
            response = APIClient.delete(f"/categories/{category_id}/parameters/{parameter['id']}")
            if response.status_code != 204:
                QMessageBox.warning(self, "Ошибка", response.json().get("detail", "Ошибка"))
            self.load_category_parameters()
        except Exception as e:
            QMessageBox.critical(self, "Ошибка подключения", str(e))
