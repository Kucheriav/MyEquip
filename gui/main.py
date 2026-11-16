import sys
from PyQt6.QtWidgets import QApplication, QDialog, QVBoxLayout, QLabel, QLineEdit, QDialogButtonBox, QMessageBox
from ui.main_window import MainWindow
from api.client import APIClient


def except_hook(cls, exception, traceback):
    sys.__excepthook__(cls, exception, traceback)


class LoginDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Вход в MyEquip")
        self.resize(320, 140)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Email:"))
        self.email_input = QLineEdit()
        layout.addWidget(self.email_input)

        layout.addWidget(QLabel("Пароль:"))
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addWidget(self.password_input)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)


def login_required_flow() -> bool:
    """If the server requires authentication, show a login dialog first.
    Returns False when the user cancelled or failed to log in."""
    if not APIClient.is_auth_required():
        return True

    dialog = LoginDialog()
    while dialog.exec() == QDialog.DialogCode.Accepted:
        ok, message = APIClient.login(
            dialog.email_input.text().strip(),
            dialog.password_input.text(),
        )
        if ok:
            return True
        QMessageBox.warning(None, "Ошибка входа", message)
    return False


def main():
    app = QApplication(sys.argv)
    if not login_required_flow():
        sys.exit(0)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
