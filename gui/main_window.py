import sys
import requests
from datetime import datetime
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTabWidget, QPushButton, QLabel, QLineEdit, QComboBox,
    QTableWidget, QTableWidgetItem, QDialog, QMessageBox,
    QSpinBox, QDateEdit, QFormLayout, QScrollArea, QGroupBox
)
from PyQt6.QtCore import Qt, QDate
from PyQt6.QtGui import QIcon

API_URL = "http://localhost:8000/api"


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("MyEquip - Equipment Tracking System")
        self.setGeometry(100, 100, 1400, 900)

        # Create central widget and main layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout()

        # Create tab widget
        self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs)

        # Add tabs
        self.tabs.addTab(self.create_clubs_tab(), "Клубы")
        self.tabs.addTab(self.create_storages_tab(), "Склады")
        self.tabs.addTab(self.create_users_tab(), "Пользователи")
        self.tabs.addTab(self.create_categories_tab(), "Категории")
        self.tabs.addTab(self.create_items_tab(), "Снаряжение")
        self.tabs.addTab(self.create_distributions_tab(), "Выдачи")
        self.tabs.addTab(self.create_breakdowns_tab(), "Поломки")

        central_widget.setLayout(main_layout)

    # ==================== CLUBS TAB ====================
    def create_clubs_tab(self):
        widget = QWidget()
        layout = QVBoxLayout()

        # Form to add club
        form_group = self.create_form_group("Добавить клуб")
        form = form_group.layout()

        self.club_name_input = QLineEdit()
        self.club_name_input.setPlaceholderText("Название клуба")
        form.addRow("Название:", self.club_name_input)

        add_club_btn = QPushButton("Добавить клуб")
        add_club_btn.clicked.connect(self.add_club)
        form.addRow(add_club_btn)

        layout.addWidget(form_group)

        # Table to display clubs
        self.clubs_table = QTableWidget()
        self.clubs_table.setColumnCount(2)
        self.clubs_table.setHorizontalHeaderLabels(["ID", "Название"])
        layout.addWidget(QLabel("Список клубов:"))
        layout.addWidget(self.clubs_table)

        refresh_btn = QPushButton("Обновить")
        refresh_btn.clicked.connect(self.load_clubs)
        layout.addWidget(refresh_btn)

        widget.setLayout(layout)
        self.load_clubs()
        return widget

    def add_club(self):
        name = self.club_name_input.text().strip()
        if not name:
            QMessageBox.warning(self, "Ошибка", "Введите название клуба")
            return

        try:
            response = requests.post(f"{API_URL}/clubs", json={"name": name})
            if response.status_code == 201:
                QMessageBox.information(self, "Успех", "Клуб добавлен")
                self.club_name_input.clear()
                self.load_clubs()
            else:
                QMessageBox.warning(self, "Ошибка", response.json().get("detail", "Ошибка при добавлении"))
        except Exception as e:
            QMessageBox.critical(self, "Ошибка подключения", str(e))

    def load_clubs(self):
        try:
            response = requests.get(f"{API_URL}/clubs")
            clubs = response.json()
            self.clubs_table.setRowCount(len(clubs))
            for row, club in enumerate(clubs):
                self.clubs_table.setItem(row, 0, QTableWidgetItem(str(club["id"])))
                self.clubs_table.setItem(row, 1, QTableWidgetItem(club["name"]))
        except Exception as e:
            QMessageBox.critical(self, "Ошибка подключения", str(e))

    # ==================== STORAGES TAB ====================
    def create_storages_tab(self):
        widget = QWidget()
        layout = QVBoxLayout()

        # Form to add storage
        form_group = self.create_form_group("Добавить склад")
        form = form_group.layout()

        self.storage_name_input = QLineEdit()
        self.storage_name_input.setPlaceholderText("Название склада")
        form.addRow("Название:", self.storage_name_input)

        self.storage_address_input = QLineEdit()
        self.storage_address_input.setPlaceholderText("Адрес")
        form.addRow("Адрес:", self.storage_address_input)

        self.storage_club_combo = QComboBox()
        form.addRow("Клуб:", self.storage_club_combo)

        add_storage_btn = QPushButton("Добавить склад")
        add_storage_btn.clicked.connect(self.add_storage)
        form.addRow(add_storage_btn)

        layout.addWidget(form_group)

        # Table
        self.storages_table = QTableWidget()
        self.storages_table.setColumnCount(4)
        self.storages_table.setHorizontalHeaderLabels(["ID", "Название", "Адрес", "Клуб"])
        layout.addWidget(QLabel("Список складов:"))
        layout.addWidget(self.storages_table)

        refresh_btn = QPushButton("Обновить")
        refresh_btn.clicked.connect(lambda: [self.load_clubs_combo(), self.load_storages()])
        layout.addWidget(refresh_btn)

        widget.setLayout(layout)
        self.load_clubs_combo()
        self.load_storages()
        return widget

    def load_clubs_combo(self):
        try:
            response = requests.get(f"{API_URL}/clubs")
            clubs = response.json()
            self.storage_club_combo.clear()
            for club in clubs:
                self.storage_club_combo.addItem(club["name"], club["id"])
        except:
            pass

    def add_storage(self):
        name = self.storage_name_input.text().strip()
        address = self.storage_address_input.text().strip()
        club_id = self.storage_club_combo.currentData()

        if not name or not club_id:
            QMessageBox.warning(self, "Ошибка", "Заполните все обязательные поля")
            return

        try:
            response = requests.post(
                f"{API_URL}/storages",
                json={"name": name, "address": address, "club_id": club_id}
            )
            if response.status_code == 201:
                QMessageBox.information(self, "Успех", "Склад добавлен")
                self.storage_name_input.clear()
                self.storage_address_input.clear()
                self.load_storages()
            else:
                QMessageBox.warning(self, "Ошибка", response.json().get("detail", "Ошибка"))
        except Exception as e:
            QMessageBox.critical(self, "Ошибка подключения", str(e))

    def load_storages(self):
        try:
            response = requests.get(f"{API_URL}/storages")
            storages = response.json()
            self.storages_table.setRowCount(len(storages))
            for row, storage in enumerate(storages):
                self.storages_table.setItem(row, 0, QTableWidgetItem(str(storage["id"])))
                self.storages_table.setItem(row, 1, QTableWidgetItem(storage["name"]))
                self.storages_table.setItem(row, 2, QTableWidgetItem(storage.get("address", "")))
                # Get club name
                try:
                    club_resp = requests.get(f"{API_URL}/clubs/{storage['club_id']}")
                    club_name = club_resp.json().get("name", "")
                    self.storages_table.setItem(row, 3, QTableWidgetItem(club_name))
                except:
                    self.storages_table.setItem(row, 3, QTableWidgetItem(""))
        except Exception as e:
            QMessageBox.critical(self, "Ошибка подключения", str(e))

    # ==================== USERS TAB ====================
    def create_users_tab(self):
        widget = QWidget()
        layout = QVBoxLayout()

        # Form to add user
        form_group = self.create_form_group("Добавить пользователя")
        form = form_group.layout()

        self.user_name_input = QLineEdit()
        self.user_name_input.setPlaceholderText("Имя")
        form.addRow("Имя:", self.user_name_input)

        self.user_surname_input = QLineEdit()
        self.user_surname_input.setPlaceholderText("Фамилия")
        form.addRow("Фамилия:", self.user_surname_input)

        self.user_lastname_input = QLineEdit()
        self.user_lastname_input.setPlaceholderText("Отчество")
        form.addRow("Отчество:", self.user_lastname_input)

        self.user_email_input = QLineEdit()
        self.user_email_input.setPlaceholderText("Email")
        form.addRow("Email:", self.user_email_input)

        self.user_phone_input = QLineEdit()
        self.user_phone_input.setPlaceholderText("+7...")
        form.addRow("Телефон:", self.user_phone_input)

        self.user_password_input = QLineEdit()
        self.user_password_input.setPlaceholderText("Пароль")
        self.user_password_input.setEchoMode(QLineEdit.EchoMode.Password)
        form.addRow("Пароль:", self.user_password_input)

        self.user_status_combo = QComboBox()
        self.user_status_combo.addItems(["guest", "unverified", "full"])
        form.addRow("Статус:", self.user_status_combo)

        add_user_btn = QPushButton("Добавить пользователя")
        add_user_btn.clicked.connect(self.add_user)
        form.addRow(add_user_btn)

        layout.addWidget(form_group)

        # Table
        self.users_table = QTableWidget()
        self.users_table.setColumnCount(6)
        self.users_table.setHorizontalHeaderLabels(["ID", "ФИО", "Email", "Телефон", "Статус", "Действия"])
        layout.addWidget(QLabel("Список пользователей:"))
        layout.addWidget(self.users_table)

        refresh_btn = QPushButton("Обновить")
        refresh_btn.clicked.connect(self.load_users)
        layout.addWidget(refresh_btn)

        widget.setLayout(layout)
        self.load_users()
        return widget

    def add_user(self):
        import hashlib

        name = self.user_name_input.text().strip()
        surname = self.user_surname_input.text().strip()
        lastname = self.user_lastname_input.text().strip()
        email = self.user_email_input.text().strip()
        phone = self.user_phone_input.text().strip()
        password = self.user_password_input.text()
        status = self.user_status_combo.currentText()

        if not all([name, surname, email, phone, password]):
            QMessageBox.warning(self, "Ошибка", "Заполните все обязательные поля")
            return

        try:
            pswd_hash = hashlib.sha256(password.encode()).hexdigest()
            response = requests.post(
                f"{API_URL}/users",
                json={
                    "name": name,
                    "surname": surname,
                    "last_name": lastname,
                    "email": email,
                    "phone": phone,
                    "pswd_hash": pswd_hash,
                    "status": status
                }
            )
            if response.status_code == 201:
                QMessageBox.information(self, "Успех", "Пользователь добавлен")
                self.user_name_input.clear()
                self.user_surname_input.clear()
                self.user_lastname_input.clear()
                self.user_email_input.clear()
                self.user_phone_input.clear()
                self.user_password_input.clear()
                self.load_users()
            else:
                QMessageBox.warning(self, "Ошибка", response.json().get("detail", "Ошибка"))
        except Exception as e:
            QMessageBox.critical(self, "Ошибка подключения", str(e))

    def load_users(self):
        try:
            response = requests.get(f"{API_URL}/users")
            users = response.json()
            self.users_table.setRowCount(len(users))
            for row, user in enumerate(users):
                self.users_table.setItem(row, 0, QTableWidgetItem(str(user["id"])))
                fio = f"{user['surname']} {user['name']} {user.get('last_name', '')}"
                self.users_table.setItem(row, 1, QTableWidgetItem(fio))
                self.users_table.setItem(row, 2, QTableWidgetItem(user["email"]))
                self.users_table.setItem(row, 3, QTableWidgetItem(user["phone"]))
                self.users_table.setItem(row, 4, QTableWidgetItem(user["status"]))
        except Exception as e:
            QMessageBox.critical(self, "Ошибка подключения", str(e))

    # ==================== CATEGORIES TAB ====================
    def create_categories_tab(self):
        widget = QWidget()
        layout = QVBoxLayout()

        # Form to add category
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

        layout.addWidget(form_group)

        # Table
        self.categories_table = QTableWidget()
        self.categories_table.setColumnCount(4)
        self.categories_table.setHorizontalHeaderLabels(["ID", "Название", "Клуб", "Родитель"])
        layout.addWidget(QLabel("Список категорий:"))
        layout.addWidget(self.categories_table)

        refresh_btn = QPushButton("Обновить")
        refresh_btn.clicked.connect(lambda: [self.load_clubs_combo(), self.load_categories()])
        layout.addWidget(refresh_btn)

        widget.setLayout(layout)
        self.load_clubs_combo()
        self.load_categories()
        return widget

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

            response = requests.post(f"{API_URL}/categories", json=data)
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
            response = requests.get(f"{API_URL}/categories")
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
                    club_resp = requests.get(f"{API_URL}/clubs/{category['club_id']}")
                    club_name = club_resp.json().get("name", "")
                    self.categories_table.setItem(row, 2, QTableWidgetItem(club_name))
                except:
                    self.categories_table.setItem(row, 2, QTableWidgetItem(""))

                parent_name = ""
                if category.get("parent_id"):
                    try:
                        parent_resp = requests.get(f"{API_URL}/categories/{category['parent_id']}")
                        parent_name = parent_resp.json().get("title", "")
                    except:
                        pass

                self.categories_table.setItem(row, 3, QTableWidgetItem(parent_name))
                self.category_parent_combo.addItem(category["title"], category["id"])
        except Exception as e:
            QMessageBox.critical(self, "Ошибка подключения", str(e))

    # ==================== ITEMS TAB ====================
    def create_items_tab(self):
        widget = QWidget()
        layout = QVBoxLayout()

        # Form to add item
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

        layout.addWidget(form_group)

        # Table
        self.items_table = QTableWidget()
        self.items_table.setColumnCount(7)
        self.items_table.setHorizontalHeaderLabels(
            ["ID", "Название", "Категория", "Склад", "Владелец", "Статус", "Серийный"])
        layout.addWidget(QLabel("Список снаряжения:"))
        layout.addWidget(self.items_table)

        refresh_btn = QPushButton("Обновить")
        refresh_btn.clicked.connect(self.load_items_data)
        layout.addWidget(refresh_btn)

        widget.setLayout(layout)
        self.load_items_data()
        return widget

    def load_items_data(self):
        self.load_categories_combo()
        self.load_storages_combo()
        self.load_users_combo()
        self.load_items()

    def load_categories_combo(self):
        try:
            response = requests.get(f"{API_URL}/categories")
            categories = response.json()
            self.item_category_combo.clear()
            for category in categories:
                self.item_category_combo.addItem(category["title"], category["id"])
        except:
            pass

    def load_storages_combo(self):
        try:
            response = requests.get(f"{API_URL}/storages")
            storages = response.json()
            self.item_storage_combo.clear()
            for storage in storages:
                self.item_storage_combo.addItem(storage["name"], storage["id"])
        except:
            pass

    def load_users_combo(self):
        try:
            response = requests.get(f"{API_URL}/users")
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

            response = requests.post(f"{API_URL}/items", json=data)
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
            response = requests.get(f"{API_URL}/items")
            items = response.json()
            self.items_table.setRowCount(len(items))

            for row, item in enumerate(items):
                self.items_table.setItem(row, 0, QTableWidgetItem(str(item["id"])))
                self.items_table.setItem(row, 1, QTableWidgetItem(item["name"]))

                # Get category name
                try:
                    cat_resp = requests.get(f"{API_URL}/categories/{item['category_id']}")
                    cat_name = cat_resp.json().get("title", "")
                    self.items_table.setItem(row, 2, QTableWidgetItem(cat_name))
                except:
                    self.items_table.setItem(row, 2, QTableWidgetItem(""))

                # Get storage name
                try:
                    stor_resp = requests.get(f"{API_URL}/storages/{item['storage_id']}")
                    stor_name = stor_resp.json().get("name", "")
                    self.items_table.setItem(row, 3, QTableWidgetItem(stor_name))
                except:
                    self.items_table.setItem(row, 3, QTableWidgetItem(""))

                # Get owner name
                try:
                    owner_resp = requests.get(f"{API_URL}/users/{item['owner_id']}")
                    owner_data = owner_resp.json()
                    owner_name = f"{owner_data['surname']} {owner_data['name']}"
                    self.items_table.setItem(row, 4, QTableWidgetItem(owner_name))
                except:
                    self.items_table.setItem(row, 4, QTableWidgetItem(""))

                self.items_table.setItem(row, 5, QTableWidgetItem(item.get("status", "")))
                self.items_table.setItem(row, 6, QTableWidgetItem(item.get("serial_number", "")))
        except Exception as e:
            QMessageBox.critical(self, "Ошибка подключения", str(e))

    # ==================== DISTRIBUTIONS TAB ====================
    def create_distributions_tab(self):
        widget = QWidget()
        layout = QVBoxLayout()

        # Form to issue item
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

        layout.addWidget(form_group)

        # Table
        self.distributions_table = QTableWidget()
        self.distributions_table.setColumnCount(8)
        self.distributions_table.setHorizontalHeaderLabels(
            ["ID", "Предмет", "Выдавший", "Получивший", "Дата выдачи", "Возврат до", "Статус", "Действия"]
        )
        layout.addWidget(QLabel("История выдачи:"))
        layout.addWidget(self.distributions_table)

        refresh_btn = QPushButton("Обновить")
        refresh_btn.clicked.connect(self.load_distributions_data)
        layout.addWidget(refresh_btn)

        widget.setLayout(layout)
        self.load_distributions_data()
        return widget

    def load_distributions_data(self):
        self.load_items_combo()
        self.load_users_combo()
        self.load_distributions()

    def load_items_combo(self):
        try:
            response = requests.get(f"{API_URL}/items")
            items = response.json()
            self.dist_item_combo.clear()
            for item in items:
                self.dist_item_combo.addItem(item["name"], item["id"])
        except:
            pass

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

            response = requests.post(f"{API_URL}/distributions", json=data)
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
            response = requests.get(f"{API_URL}/distributions")
            distributions = response.json()
            self.distributions_table.setRowCount(len(distributions))

            for row, dist in enumerate(distributions):
                self.distributions_table.setItem(row, 0, QTableWidgetItem(str(dist["id"])))

                # Get item name
                try:
                    item_resp = requests.get(f"{API_URL}/items/{dist['item_id']}")
                    item_name = item_resp.json().get("name", "")
                    self.distributions_table.setItem(row, 1, QTableWidgetItem(item_name))
                except:
                    self.distributions_table.setItem(row, 1, QTableWidgetItem(""))

                # Get giver name
                try:
                    giver_resp = requests.get(f"{API_URL}/users/{dist['giver_id']}")
                    giver_data = giver_resp.json()
                    giver_name = f"{giver_data['surname']} {giver_data['name']}"
                    self.distributions_table.setItem(row, 2, QTableWidgetItem(giver_name))
                except:
                    self.distributions_table.setItem(row, 2, QTableWidgetItem(""))

                # Get getter name
                try:
                    getter_resp = requests.get(f"{API_URL}/users/{dist['getter_id']}")
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
            response = requests.put(f"{API_URL}/distributions/{distribution_id}", json=data)
            if response.status_code == 200:
                QMessageBox.information(self, "Успех", "Предмет отмечен как возвращенный")
                self.load_distributions()
            else:
                QMessageBox.warning(self, "Ошибка", "Ошибка при возврате")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка подключения", str(e))

    # ==================== BREAKDOWNS TAB ====================
    def create_breakdowns_tab(self):
        widget = QWidget()
        layout = QVBoxLayout()

        # Form to report breakdown
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

        layout.addWidget(form_group)

        # Table
        self.breakdowns_table = QTableWidget()
        self.breakdowns_table.setColumnCount(7)
        self.breakdowns_table.setHorizontalHeaderLabels(
            ["ID", "Предмет", "Описание", "Дата поломки", "Отремонтирована", "Мастер", "Действи��"]
        )
        layout.addWidget(QLabel("Список поломок:"))
        layout.addWidget(self.breakdowns_table)

        refresh_btn = QPushButton("Обновить")
        refresh_btn.clicked.connect(self.load_breakdowns_data)
        layout.addWidget(refresh_btn)

        widget.setLayout(layout)
        self.load_breakdowns_data()
        return widget

    def load_breakdowns_data(self):
        self.load_items_combo()
        self.load_users_combo()
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

            response = requests.post(f"{API_URL}/breakdowns", json=data)
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
            response = requests.get(f"{API_URL}/breakdowns")
            breakdowns = response.json()
            self.breakdowns_table.setRowCount(len(breakdowns))

            for row, breakdown in enumerate(breakdowns):
                self.breakdowns_table.setItem(row, 0, QTableWidgetItem(str(breakdown["id"])))

                # Get item name
                try:
                    item_resp = requests.get(f"{API_URL}/items/{breakdown['item_id']}")
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
                        repairer_resp = requests.get(f"{API_URL}/users/{breakdown['repairer_id']}")
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
            response = requests.put(f"{API_URL}/breakdowns/{breakdown_id}", json=data)
            if response.status_code == 200:
                QMessageBox.information(self, "Успех", "Предмет отмечен как отремонтированный")
                self.load_breakdowns()
            else:
                QMessageBox.warning(self, "Ошибка", "Ошибка при обновлении")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка подключения", str(e))

    # ==================== HELPER METHODS ====================
    def create_form_group(self, title):
        group = QGroupBox(title)
        layout = QFormLayout()
        group.setLayout(layout)
        return group


def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()