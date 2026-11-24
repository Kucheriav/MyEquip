import logging
import sys
from PyQt6.QtWidgets import (
    QApplication, QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QMessageBox, QFormLayout, QWidget, QStackedWidget,
)

try:
    # normal case: running with the project root on sys.path (PyCharm / cwd=root)
    from gui.api.client import APIClient
    from gui.ui.main_window import MainWindow
    from gui.logging_config import setup_gui_logging
except ImportError:
    # fallback: running from inside the gui/ directory
    from api.client import APIClient
    from ui.main_window import MainWindow
    from logging_config import setup_gui_logging

logger = logging.getLogger("gui")


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

    # ---------- login page ----------
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

    # ---------- register page ----------
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

    # ---------- actions ----------
    def _try_login(self):
        login = self.login_input.text().strip()
        password = self.login_password_input.text()
        if not login or not password:
            QMessageBox.warning(self, "Ошибка", "Введите логин и пароль")
            return
        ok, message = APIClient.login(login, password)
        if ok:
            logger.info("login ok")
            self.accept()
        else:
            logger.warning("login failed: %s", message)
            QMessageBox.warning(self, "Ошибка входа", message)

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
        ok, message = APIClient.register(data)
        if ok:
            logger.info("registration ok")
            self.accept()
        else:
            logger.warning("registration failed: %s", message)
            QMessageBox.warning(self, "Ошибка регистрации", message)


def main():
    setup_gui_logging()
    logger.info("GUI starting")
    app = QApplication(sys.argv)
    start = StartDialog()
    if start.exec() != QDialog.DialogCode.Accepted:
        sys.exit(0)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
