from PyQt6.QtWidgets import (
    QPushButton, QLabel, QLineEdit, QTableWidget, QTableWidgetItem, QMessageBox, QComboBox
)
from gui.api.client import APIClient
from . import BaseTab


class CategoriesTab(BaseTab):
    def __init__(self):
        super().__init__()
        self.init_ui()
        # self.load_categories()

    def init_ui(self):
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

        # Table
        self.categories_table = QTableWidget()
        self.categories_table.setColumnCount(4)
        self.categories_table.setHorizontalHeaderLabels(["ID", "Название", "Клуб", "Родитель"])
        self.layout.addWidget(QLabel("Список категорий:"))
        self.layout.addWidget(self.categories_table)

        refresh_btn = QPushButton("Обновить")
        refresh_btn.clicked.connect(self.load_categories)
        self.layout.addWidget(refresh_btn)

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

            # Reload parent combo
            self.category_parent_combo.clear()
            self.category_parent_combo.addItem("Нет", None)

            for row, category in enumerate(categories):
                self.categories_table.setItem(row, 0, QTableWidgetItem(str(category["id"])))
                self.categories_table.setItem(row, 1, QTableWidgetItem(category["title"]))

                # Get club name
                try:
                    club_resp = APIClient.get(f"/clubs/{category['club_id']}")
                    club_name = club_resp.json().get("name", "")
                    self.categories_table.setItem(row, 2, QTableWidgetItem(club_name))
                except:
                    self.categories_table.setItem(row, 2, QTableWidgetItem(""))

                parent_name = ""
                if category.get("parent_id"):
                    try:
                        parent_resp = APIClient.get(f"/categories/{category['parent_id']}")
                        parent_name = parent_resp.json().get("title", "")
                    except:
                        pass

                self.categories_table.setItem(row, 3, QTableWidgetItem(parent_name))
                self.category_parent_combo.addItem(category["title"], category["id"])
        except Exception as e:
            QMessageBox.critical(self, "Ошибка подключения", str(e))