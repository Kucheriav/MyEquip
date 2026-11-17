from PyQt6.QtWidgets import (
    QPushButton, QLabel, QLineEdit, QTableWidget, QTableWidgetItem, QMessageBox, QComboBox
)
from gui.api.client import APIClient
from . import BaseTab


class UsersTab(BaseTab):
    def __init__(self):
        super().__init__()
        self.init_ui()
        self.load_users()

    def init_ui(self):
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

        self.layout.addWidget(form_group)

        # Table
        self.users_table = QTableWidget()
        self.users_table.setColumnCount(6)
        self.users_table.setHorizontalHeaderLabels(["ID", "ФИО", "Email", "Телефон", "Статус", "Действия"])
        self.layout.addWidget(QLabel("Список пользователей:"))
        self.layout.addWidget(self.users_table)

        refresh_btn = QPushButton("Обновить")
        refresh_btn.clicked.connect(self.load_users)
        self.layout.addWidget(refresh_btn)

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
            response = APIClient.post(
                "/users",
                {
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
            response = APIClient.get("/users")
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