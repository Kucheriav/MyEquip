import sys
import requests
from datetime import datetime
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTabWidget, QPushButton, QLabel, QLineEdit, QComboBox,
    QTableWidget, QTableWidgetItem, QDialog, QMessageBox,
    QSpinBox, QDateEdit, QFormLayout, QScrollArea, QGroupBox,
    QStackedWidget
)
from PyQt6.QtCore import Qt, QDate
from PyQt6.QtGui import QIcon

API_URL = "http://localhost:8000/api"

# Shared session: carries the Authorization header after login/registration
session = requests.Session()


def set_auth_token(token: str):
    if token:
        session.headers.update({"Authorization": f"Bearer {token}"})


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
        self.tabs.addTab(self.create_transfers_tab(), "Перемещения")
        self.tabs.addTab(self.create_breakdowns_tab(), "Поломки")

        central_widget.setLayout(main_layout)

        # Rebuild dropdowns of a tab when it becomes visible: data added
        # in another tab (a new club, user, item...) must appear in them.
        self.tabs.currentChanged.connect(self.on_tab_changed)

    # Map: tab index -> combo-refresh method (cross-tab data only)
    def on_tab_changed(self, index: int):
        refresh_map = {
            1: self.load_clubs_combo,        # Склады: клубы
            3: self.load_category_clubs_combo,  # Категории: клубы
            4: self.refresh_item_combos,     # Снаряжение: категории, склады, владельцы
            5: self.refresh_dist_combos,     # Выдачи: предметы, выдающий/получающий
            6: self.load_transfer_combos,    # Перемещения: предметы, передающий, склады
            7: self.load_breakdown_combos,   # Поломки: предметы, мастер
        }
        refresh = refresh_map.get(index)
        if refresh:
            refresh()

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
            response = session.post(f"{API_URL}/clubs", json={"name": name})
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
            response = session.get(f"{API_URL}/clubs")
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
            response = session.get(f"{API_URL}/clubs")
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
            response = session.post(
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
            response = session.get(f"{API_URL}/storages")
            storages = response.json()
            self.storages_table.setRowCount(len(storages))
            for row, storage in enumerate(storages):
                self.storages_table.setItem(row, 0, QTableWidgetItem(str(storage["id"])))
                self.storages_table.setItem(row, 1, QTableWidgetItem(storage["name"]))
                self.storages_table.setItem(row, 2, QTableWidgetItem(storage.get("address", "")))
                # Get club name
                try:
                    club_resp = session.get(f"{API_URL}/clubs/{storage['club_id']}")
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
        self.user_email_input.setPlaceholderText("Email (необязательно)")
        form.addRow("Email:", self.user_email_input)

        self.user_phone_input = QLineEdit()
        self.user_phone_input.setPlaceholderText("+7...")
        form.addRow("Телефон:", self.user_phone_input)

        self.user_password_input = QLineEdit()
        self.user_password_input.setPlaceholderText("Пароль (необязательно: пусто = турист без аккаунта)")
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

        if not all([name, surname, phone]):
            QMessageBox.warning(self, "Ошибка", "Заполните обязательные поля (имя, фамилия, телефон)")
            return

        try:
            pswd_hash = hashlib.sha256(password.encode()).hexdigest() if password else None
            response = session.post(
                f"{API_URL}/users",
                json={
                    "name": name,
                    "surname": surname,
                    "last_name": lastname,
                    "email": email or None,
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
            response = session.get(f"{API_URL}/users")
            users = response.json()
            self.users_table.setRowCount(len(users))
            for row, user in enumerate(users):
                self.users_table.setItem(row, 0, QTableWidgetItem(str(user["id"])))
                fio = f"{user['surname']} {user['name']} {user.get('last_name', '')}"
                self.users_table.setItem(row, 1, QTableWidgetItem(fio))
                self.users_table.setItem(row, 2, QTableWidgetItem(user["email"] or ""))
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
        refresh_btn.clicked.connect(lambda: [self.load_category_clubs_combo(), self.load_categories()])
        layout.addWidget(refresh_btn)

        widget.setLayout(layout)
        self.load_category_clubs_combo()
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

            response = session.post(f"{API_URL}/categories", json=data)
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
            response = session.get(f"{API_URL}/categories")
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
                    club_resp = session.get(f"{API_URL}/clubs/{category['club_id']}")
                    club_name = club_resp.json().get("name", "")
                    self.categories_table.setItem(row, 2, QTableWidgetItem(club_name))
                except:
                    self.categories_table.setItem(row, 2, QTableWidgetItem(""))

                parent_name = ""
                if category.get("parent_id"):
                    try:
                        parent_resp = session.get(f"{API_URL}/categories/{category['parent_id']}")
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
            response = session.get(f"{API_URL}/categories")
            categories = response.json()
            self.item_category_combo.clear()
            for category in categories:
                self.item_category_combo.addItem(category["title"], category["id"])
        except:
            pass

    def load_storages_combo(self):
        try:
            response = session.get(f"{API_URL}/storages")
            storages = response.json()
            self.item_storage_combo.clear()
            for storage in storages:
                self.item_storage_combo.addItem(storage["name"], storage["id"])
        except:
            pass

    def load_users_combo(self):
        try:
            response = session.get(f"{API_URL}/users")
            users = response.json()
            self.item_owner_combo.clear()
            for user in users:
                fio = f"{user['surname']} {user['name']}"
                self.item_owner_combo.addItem(fio, user["id"])
        except:
            pass

    def load_category_clubs_combo(self):
        """The category form's club dropdown (filled from the Clubs tab data)."""
        try:
            response = session.get(f"{API_URL}/clubs")
            clubs = response.json()
            self.category_club_combo.clear()
            for club in clubs:
                self.category_club_combo.addItem(club["name"], club["id"])
        except:
            pass

    def refresh_item_combos(self):
        self.load_categories_combo()
        self.load_storages_combo()
        self.load_users_combo()

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

            response = session.post(f"{API_URL}/items", json=data)
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
            response = session.get(f"{API_URL}/items")
            items = response.json()
            self.items_table.setRowCount(len(items))

            for row, item in enumerate(items):
                self.items_table.setItem(row, 0, QTableWidgetItem(str(item["id"])))
                self.items_table.setItem(row, 1, QTableWidgetItem(item["name"]))

                # Get category name
                try:
                    cat_resp = session.get(f"{API_URL}/categories/{item['category_id']}")
                    cat_name = cat_resp.json().get("title", "")
                    self.items_table.setItem(row, 2, QTableWidgetItem(cat_name))
                except:
                    self.items_table.setItem(row, 2, QTableWidgetItem(""))

                # Get storage name
                try:
                    stor_resp = session.get(f"{API_URL}/storages/{item['storage_id']}")
                    stor_name = stor_resp.json().get("name", "")
                    self.items_table.setItem(row, 3, QTableWidgetItem(stor_name))
                except:
                    self.items_table.setItem(row, 3, QTableWidgetItem(""))

                # Get owner name
                try:
                    owner_resp = session.get(f"{API_URL}/users/{item['owner_id']}")
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
        self.load_dist_users_combo()
        self.load_distributions()

    def load_dist_users_combo(self):
        """Fill giver/getter dropdowns of the distributions tab."""
        try:
            response = session.get(f"{API_URL}/users")
            users = response.json()
            self.dist_giver_combo.clear()
            self.dist_getter_combo.clear()
            for user in users:
                fio = f"{user['surname']} {user['name']}"
                self.dist_giver_combo.addItem(fio, user["id"])
                self.dist_getter_combo.addItem(fio, user["id"])
        except:
            pass

    def refresh_dist_combos(self):
        self.load_items_combo()
        self.load_dist_users_combo()

    def load_items_combo(self):
        try:
            response = session.get(f"{API_URL}/items")
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

            response = session.post(f"{API_URL}/distributions", json=data)
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
            response = session.get(f"{API_URL}/distributions")
            distributions = response.json()
            self.distributions_table.setRowCount(len(distributions))

            for row, dist in enumerate(distributions):
                self.distributions_table.setItem(row, 0, QTableWidgetItem(str(dist["id"])))

                # Get item name
                try:
                    item_resp = session.get(f"{API_URL}/items/{dist['item_id']}")
                    item_name = item_resp.json().get("name", "")
                    self.distributions_table.setItem(row, 1, QTableWidgetItem(item_name))
                except:
                    self.distributions_table.setItem(row, 1, QTableWidgetItem(""))

                # Get giver name
                try:
                    giver_resp = session.get(f"{API_URL}/users/{dist['giver_id']}")
                    giver_data = giver_resp.json()
                    giver_name = f"{giver_data['surname']} {giver_data['name']}"
                    self.distributions_table.setItem(row, 2, QTableWidgetItem(giver_name))
                except:
                    self.distributions_table.setItem(row, 2, QTableWidgetItem(""))

                # Get getter name
                try:
                    getter_resp = session.get(f"{API_URL}/users/{dist['getter_id']}")
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
            response = session.put(f"{API_URL}/distributions/{distribution_id}", json=data)
            if response.status_code == 200:
                QMessageBox.information(self, "Успех", "Предмет отмечен как возвращенный")
                self.load_distributions()
            else:
                QMessageBox.warning(self, "Ошибка", "Ошибка при возврате")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка подключения", str(e))

    # ==================== TRANSFERS TAB ====================
    def create_transfers_tab(self):
        widget = QWidget()
        layout = QVBoxLayout()

        # Form to transfer item between storages
        form_group = self.create_form_group("Переместить снаряжение")
        form = form_group.layout()

        self.transfer_item_combo = QComboBox()
        self.transfer_item_combo.currentIndexChanged.connect(self.on_transfer_item_selected)
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

        layout.addWidget(form_group)

        # Table
        self.transfers_table = QTableWidget()
        self.transfers_table.setColumnCount(6)
        self.transfers_table.setHorizontalHeaderLabels(
            ["ID", "Предмет", "Откуда", "Куда", "Дата", "Комментарий"]
        )
        layout.addWidget(QLabel("История перемещений:"))
        layout.addWidget(self.transfers_table)

        refresh_btn = QPushButton("Обновить")
        refresh_btn.clicked.connect(self.load_transfers_data)
        layout.addWidget(refresh_btn)

        widget.setLayout(layout)
        self.load_transfers_data()
        return widget

    def load_transfers_data(self):
        self.load_transfer_combos()
        self.load_transfers()

    def load_transfer_combos(self):
        # Items
        try:
            response = session.get(f"{API_URL}/items")
            items = response.json()
            self.transfer_item_combo.blockSignals(True)
            self.transfer_item_combo.clear()
            for item in items:
                self.transfer_item_combo.addItem(item["name"], item["id"])
            self.transfer_item_combo.blockSignals(False)
        except:
            pass
        # Users (mover)
        try:
            response = session.get(f"{API_URL}/users")
            users = response.json()
            self.transfer_mover_combo.clear()
            for user in users:
                self.transfer_mover_combo.addItem(f"{user['surname']} {user['name']}", user["id"])
        except:
            pass
        # Destination storages
        try:
            response = session.get(f"{API_URL}/storages")
            storages = response.json()
            self.transfer_to_combo.clear()
            for storage in storages:
                self.transfer_to_combo.addItem(storage["name"], storage["id"])
        except:
            pass
        self.on_transfer_item_selected()

    def on_transfer_item_selected(self):
        item_id = self.transfer_item_combo.currentData()
        if not item_id:
            self.transfer_from_label.setText("—")
            return
        try:
            response = session.get(f"{API_URL}/items/{item_id}")
            item = response.json()
            storage_id = item.get("storage_id")
            storage_name = ""
            if storage_id:
                try:
                    storage_resp = session.get(f"{API_URL}/storages/{storage_id}")
                    storage_name = storage_resp.json().get("name", "")
                except:
                    pass
            self.transfer_from_label.setText(f"{storage_name} (id {storage_id})")
        except:
            self.transfer_from_label.setText("—")

    def make_transfer(self):
        item_id = self.transfer_item_combo.currentData()
        mover_id = self.transfer_mover_combo.currentData()
        to_storage_id = self.transfer_to_combo.currentData()
        comment = self.transfer_comment_input.text().strip()

        if not all([item_id, to_storage_id]):
            QMessageBox.warning(self, "Ошибка", "Выберите предмет и склад назначения")
            return

        # Source storage is the item's current storage
        try:
            item_resp = session.get(f"{API_URL}/items/{item_id}")
            item = item_resp.json()
            from_storage_id = item.get("storage_id")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка подключения", str(e))
            return

        if not from_storage_id:
            QMessageBox.warning(self, "Ошибка", "Не удалось определить текущий склад предмета")
            return
        if from_storage_id == to_storage_id:
            QMessageBox.warning(self, "Ошибка", "Предмет уже находится на этом складе")
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

            response = session.post(f"{API_URL}/transfers", json=data)
            if response.status_code == 201:
                QMessageBox.information(self, "Успех", "Предмет перемещён")
                self.transfer_comment_input.clear()
                self.load_transfers_data()
            else:
                QMessageBox.warning(self, "Ошибка", response.json().get("detail", "Ошибка"))
        except Exception as e:
            QMessageBox.critical(self, "Ошибка подключения", str(e))

    def load_transfers(self):
        try:
            response = session.get(f"{API_URL}/transfers")
            transfers = response.json()
            self.transfers_table.setRowCount(len(transfers))

            for row, transfer in enumerate(transfers):
                self.transfers_table.setItem(row, 0, QTableWidgetItem(str(transfer["id"])))

                item_name = ""
                try:
                    item_name = session.get(f"{API_URL}/items/{transfer['item_id']}").json().get("name", "")
                except:
                    pass
                self.transfers_table.setItem(row, 1, QTableWidgetItem(item_name))

                from_name = to_name = ""
                try:
                    from_name = session.get(f"{API_URL}/storages/{transfer['from_storage_id']}").json().get("name", "")
                    to_name = session.get(f"{API_URL}/storages/{transfer['to_storage_id']}").json().get("name", "")
                except:
                    pass
                self.transfers_table.setItem(row, 2, QTableWidgetItem(from_name))
                self.transfers_table.setItem(row, 3, QTableWidgetItem(to_name))

                self.transfers_table.setItem(row, 4, QTableWidgetItem(transfer.get("date", "")))
                self.transfers_table.setItem(row, 5, QTableWidgetItem(transfer.get("comment") or ""))
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
        self.load_breakdown_combos()
        self.load_breakdowns()

    def load_breakdown_combos(self):
        """Fill item and repairer dropdowns of the breakdowns tab."""
        # Items
        try:
            response = session.get(f"{API_URL}/items")
            items = response.json()
            self.breakdown_item_combo.clear()
            for item in items:
                self.breakdown_item_combo.addItem(item["name"], item["id"])
        except:
            pass
        # Repairer (users, with the 'Нет' option first)
        try:
            response = session.get(f"{API_URL}/users")
            users = response.json()
            current = self.breakdown_repairer_combo.currentData()
            self.breakdown_repairer_combo.clear()
            self.breakdown_repairer_combo.addItem("Нет", None)
            for user in users:
                fio = f"{user['surname']} {user['name']}"
                self.breakdown_repairer_combo.addItem(fio, user["id"])
            if current is not None:
                index = self.breakdown_repairer_combo.findData(current)
                if index >= 0:
                    self.breakdown_repairer_combo.setCurrentIndex(index)
        except:
            pass

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

            response = session.post(f"{API_URL}/breakdowns", json=data)
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
            response = session.get(f"{API_URL}/breakdowns")
            breakdowns = response.json()
            self.breakdowns_table.setRowCount(len(breakdowns))

            for row, breakdown in enumerate(breakdowns):
                self.breakdowns_table.setItem(row, 0, QTableWidgetItem(str(breakdown["id"])))

                # Get item name
                try:
                    item_resp = session.get(f"{API_URL}/items/{breakdown['item_id']}")
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
                        repairer_resp = session.get(f"{API_URL}/users/{breakdown['repairer_id']}")
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
            response = session.put(f"{API_URL}/breakdowns/{breakdown_id}", json=data)
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


class StartDialog(QDialog):
    """First screen: Login or Register (with invite code). No anonymous mode."""

    PAGE_LOGIN = 0
    PAGE_REGISTER = 1

    def __init__(self):
        super().__init__()
        self.setWindowTitle("MyEquip — вход")
        self.resize(360, 260)

        self.stack = QStackedWidget()
        layout = QVBoxLayout(self)
        layout.addWidget(self.stack)
        self.stack.addWidget(self._make_login_page())
        self.stack.addWidget(self._make_register_page())
        self.stack.setCurrentIndex(self.PAGE_LOGIN)

    def _make_login_page(self):
        page = QWidget()
        form = QFormLayout(page)

        title = QLabel("<b>Вход в MyEquip</b>")
        form.addRow(title)

        self.login_input = QLineEdit()
        self.login_input.setPlaceholderText("Телефон или email")
        form.addRow("Логин:", self.login_input)

        self.login_password_input = QLineEdit()
        self.login_password_input.setEchoMode(QLineEdit.EchoMode.Password)
        form.addRow("Пароль:", self.login_password_input)

        login_btn = QPushButton("Войти")
        login_btn.setDefault(True)
        login_btn.clicked.connect(self._try_login)
        form.addRow(login_btn)

        to_register_btn = QPushButton("Зарегистрироваться (по инвайт-коду)")
        to_register_btn.clicked.connect(lambda: self.stack.setCurrentIndex(self.PAGE_REGISTER))
        form.addRow(to_register_btn)
        return page

    def _make_register_page(self):
        page = QWidget()
        form = QFormLayout(page)

        title = QLabel("<b>Регистрация руководителя</b>")
        form.addRow(title)

        self.reg_name_input = QLineEdit()
        form.addRow("Имя:", self.reg_name_input)

        self.reg_surname_input = QLineEdit()
        form.addRow("Фамилия:", self.reg_surname_input)

        self.reg_phone_input = QLineEdit()
        self.reg_phone_input.setPlaceholderText("+7...")
        form.addRow("Телефон:*", self.reg_phone_input)

        self.reg_email_input = QLineEdit()
        self.reg_email_input.setPlaceholderText("необязательно")
        form.addRow("Email:", self.reg_email_input)

        self.reg_password_input = QLineEdit()
        self.reg_password_input.setEchoMode(QLineEdit.EchoMode.Password)
        form.addRow("Пароль:*", self.reg_password_input)

        self.reg_invite_input = QLineEdit()
        self.reg_invite_input.setPlaceholderText("инвайт-код от руководителя")
        form.addRow("Инвайт-код:*", self.reg_invite_input)

        hint = QLabel(
            "Если телефон уже есть в базе (вас записали как туриста),\n"
            "регистрация подтянет вашу историю — данные не потеряются."
        )
        hint.setStyleSheet("color: gray; font-size: 8pt;")
        form.addRow(hint)

        register_btn = QPushButton("Зарегистрироваться")
        register_btn.setDefault(True)
        register_btn.clicked.connect(self._try_register)
        form.addRow(register_btn)

        to_login_btn = QPushButton("← Назад ко входу")
        to_login_btn.clicked.connect(lambda: self.stack.setCurrentIndex(self.PAGE_LOGIN))
        form.addRow(to_login_btn)
        return page

    def _try_login(self):
        login = self.login_input.text().strip()
        password = self.login_password_input.text()
        if not login or not password:
            QMessageBox.warning(self, "Ошибка", "Введите логин и пароль")
            return
        try:
            response = requests.post(
                f"{API_URL}/auth/login",
                json={"login": login, "password": password},
            )
            if response.status_code == 200:
                set_auth_token(response.json()["access_token"])
                self.accept()
            else:
                QMessageBox.warning(self, "Ошибка входа", response.json().get("detail", "Ошибка"))
        except Exception as e:
            QMessageBox.critical(self, "Ошибка подключения", str(e))

    def _try_register(self):
        data = {
            "name": self.reg_name_input.text().strip(),
            "surname": self.reg_surname_input.text().strip(),
            "phone": self.reg_phone_input.text().strip(),
            "email": self.reg_email_input.text().strip() or None,
            "password": self.reg_password_input.text(),
            "invite_code": self.reg_invite_input.text().strip(),
        }
        if not data["name"] or not data["surname"] or not data["phone"] or not data["password"] or not data["invite_code"]:
            QMessageBox.warning(self, "Ошибка", "Заполните все обязательные поля (*)")
            return
        try:
            response = requests.post(f"{API_URL}/auth/register", json=data)
            if response.status_code != 201:
                QMessageBox.warning(self, "Ошибка регистрации", response.json().get("detail", "Ошибка"))
                return
            # Auto-login after successful registration
            login_resp = requests.post(
                f"{API_URL}/auth/login",
                json={"login": data["phone"], "password": data["password"]},
            )
            if login_resp.status_code == 200:
                set_auth_token(login_resp.json()["access_token"])
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Ошибка подключения", str(e))


def main():
    app = QApplication(sys.argv)
    start = StartDialog()
    if start.exec() != QDialog.DialogCode.Accepted:
        sys.exit(0)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()