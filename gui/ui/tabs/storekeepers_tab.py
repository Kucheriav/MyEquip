from PyQt6.QtWidgets import (
    QPushButton, QLabel, QLineEdit, QTableWidget, QTableWidgetItem, QMessageBox,
    QComboBox, QGroupBox, QFormLayout, QHBoxLayout, QWidget
)
from gui.api.client import APIClient
from . import BaseTab


class StorekeepersTab(BaseTab):
    """Leader-only tab: invite storekeepers to a club, see them, grant
    them extra clubs, and generate invites for new independent leaders."""

    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        # ---------- invite a storekeeper ----------
        invite_group = self.create_form_group("Инвайт для завхоза")
        invite_form = invite_group.layout()

        self.sk_club_combo = QComboBox()
        self.sk_club_combo.currentIndexChanged.connect(self.load_members)
        invite_form.addRow("Клуб:", self.sk_club_combo)

        invite_btn = QPushButton("Создать инвайт-код для завхоза")
        invite_btn.clicked.connect(self.create_storekeeper_invite)
        invite_form.addRow(invite_btn)

        self.sk_invite_output = QLineEdit()
        self.sk_invite_output.setReadOnly(True)
        self.sk_invite_output.setPlaceholderText("Здесь появится код — передайте его завхозу")
        invite_form.addRow("Код:", self.sk_invite_output)

        # ---------- invite another leader ----------
        leader_group = self.create_form_group("Инвайт для нового руководителя")
        leader_form = leader_group.layout()
        leader_btn = QPushButton("Создать инвайт-код для руководителя")
        leader_btn.clicked.connect(self.create_leader_invite)
        leader_form.addRow(leader_btn)

        self.leader_invite_output = QLineEdit()
        self.leader_invite_output.setReadOnly(True)
        self.leader_invite_output.setPlaceholderText("Новый руководитель начнёт без клубов")
        leader_form.addRow("Код:", self.leader_invite_output)

        row = QHBoxLayout()
        row.addWidget(invite_group)
        row.addWidget(leader_group)
        container = QWidget()
        container.setLayout(row)
        self.layout.addWidget(container)

        # ---------- grant an existing user access to a club ----------
        grant_group = self.create_form_group("Выдать завхозу доступ к клубу")
        grant_form = grant_group.layout()

        self.sk_user_combo = QComboBox()
        grant_form.addRow("Пользователь:", self.sk_user_combo)

        self.sk_grant_club_combo = QComboBox()
        grant_form.addRow("Клуб:", self.sk_grant_club_combo)

        grant_btn = QPushButton("Назначить завхозом клуба")
        grant_btn.clicked.connect(self.grant_storekeeper)
        grant_form.addRow(grant_btn)

        self.layout.addWidget(grant_group)

        # ---------- storekeeper list ----------
        self.sk_table = QTableWidget()
        self.sk_table.setColumnCount(5)
        self.sk_table.setHorizontalHeaderLabels(
            ["ID", "ФИО", "Телефон", "Клуб", "Действия"])
        self.layout.addWidget(QLabel("Завхозы:"))
        self.layout.addWidget(self.sk_table)

        refresh_btn = QPushButton("Обновить")
        refresh_btn.clicked.connect(self.load_data)
        self.layout.addWidget(refresh_btn)

    # ---------- data ----------
    def load_data(self):
        self.load_clubs_combos()
        self.load_users_combo()
        self.load_members()

    def refresh_combos(self):
        self.load_clubs_combos()
        self.load_users_combo()

    def load_clubs_combos(self):
        try:
            clubs = APIClient.get("/clubs").json()
            for combo in (self.sk_club_combo, self.sk_grant_club_combo):
                current = combo.currentData()
                combo.blockSignals(True)
                combo.clear()
                for club in clubs:
                    combo.addItem(club["name"], club["id"])
                if current is not None:
                    index = combo.findData(current)
                    if index >= 0:
                        combo.setCurrentIndex(index)
                combo.blockSignals(False)
        except Exception:
            pass

    def load_users_combo(self):
        try:
            users = APIClient.get("/users").json()
            self.sk_user_combo.clear()
            for user in users:
                fio = f"{user['surname']} {user['name']}"
                if user.get("phone"):
                    fio += f" ({user['phone']})"
                self.sk_user_combo.addItem(fio, user["id"])
        except Exception:
            pass

    # ---------- actions ----------
    def create_storekeeper_invite(self):
        club_id = self.sk_club_combo.currentData()
        if not club_id:
            QMessageBox.warning(self, "Ошибка", "Сначала выберите клуб")
            return
        try:
            response = APIClient.post(
                "/invites", {"role": "storekeeper", "club_id": club_id})
            if response.status_code == 201:
                code = response.json()["code"]
                self.sk_invite_output.setText(code)
                QMessageBox.information(self, "Инвайт создан", f"Код для завхоза: {code}")
            else:
                QMessageBox.warning(self, "Ошибка", response.json().get("detail", "Ошибка"))
        except Exception as e:
            QMessageBox.critical(self, "Ошибка подключения", str(e))

    def create_leader_invite(self):
        try:
            response = APIClient.post("/invites", {"role": "leader"})
            if response.status_code == 201:
                code = response.json()["code"]
                self.leader_invite_output.setText(code)
                QMessageBox.information(self, "Инвайт создан", f"Код для руководителя: {code}")
            else:
                QMessageBox.warning(self, "Ошибка", response.json().get("detail", "Ошибка"))
        except Exception as e:
            QMessageBox.critical(self, "Ошибка подключения", str(e))

    def grant_storekeeper(self):
        user_id = self.sk_user_combo.currentData()
        club_id = self.sk_grant_club_combo.currentData()
        if not user_id or not club_id:
            QMessageBox.warning(self, "Ошибка", "Выберите пользователя и клуб")
            return
        try:
            response = APIClient.post(
                f"/clubs/{club_id}/members",
                {"user_id": user_id, "role": "storekeeper"},
            )
            if response.status_code == 201:
                QMessageBox.information(self, "Готово", "Пользователь назначен завхозом клуба")
                self.load_members()
            else:
                QMessageBox.warning(self, "Ошибка", response.json().get("detail", "Ошибка"))
        except Exception as e:
            QMessageBox.critical(self, "Ошибка подключения", str(e))

    def remove_storekeeper(self, club_id: int, user_id: int):
        try:
            response = APIClient.delete(f"/clubs/{club_id}/members/{user_id}")
            if response.status_code == 204:
                self.load_members()
            else:
                QMessageBox.warning(self, "Ошибка", response.json().get("detail", "Ошибка"))
        except Exception as e:
            QMessageBox.critical(self, "Ошибка подключения", str(e))

    def load_members(self):
        club_id = self.sk_club_combo.currentData()
        if not club_id:
            self.sk_table.setRowCount(0)
            return
        try:
            members = APIClient.get(f"/clubs/{club_id}/members").json()
            storekeepers = [m for m in members if m.get("role") == "storekeeper"]
            self.sk_table.setRowCount(len(storekeepers))
            for row, member in enumerate(storekeepers):
                user = member.get("user") or {}
                fio = f"{user.get('surname', '')} {user.get('name', '')}".strip()
                self.sk_table.setItem(row, 0, QTableWidgetItem(str(member.get("user_id"))))
                self.sk_table.setItem(row, 1, QTableWidgetItem(fio))
                self.sk_table.setItem(row, 2, QTableWidgetItem(user.get("phone") or ""))
                self.sk_table.setItem(row, 3, QTableWidgetItem(self.sk_club_combo.currentText()))
                remove_btn = QPushButton("Убрать из клуба")
                remove_btn.clicked.connect(
                    lambda checked, c=club_id, u=member.get("user_id"):
                    self.remove_storekeeper(c, u))
                self.sk_table.setCellWidget(row, 4, remove_btn)
        except Exception as e:
            QMessageBox.critical(self, "Ошибка подключения", str(e))
