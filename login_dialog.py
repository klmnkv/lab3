"""
login_dialog.py — Диалог авторизации.
Логин и пароль берутся из учётных данных PostgreSQL: пользователь вводит
свой PostgreSQL username/password, программа пытается открыть соединение
этими кредами. Если PostgreSQL принял аутентификацию — доступ разрешён.
"""

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QDialog, QLabel, QLineEdit, QPushButton,
    QVBoxLayout, QFormLayout, QHBoxLayout, QMessageBox, QCheckBox
)
from PyQt5.QtSql import QSqlDatabase

from db_config import DB_HOST, DB_PORT, DB_NAME, DB_USER


class LoginDialog(QDialog):
    """Диалог ввода логина/пароля PostgreSQL."""

    CONNECTION_NAME = "auth_probe"

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Авторизация — educationDB")
        self.setModal(True)
        self.setMinimumWidth(360)

        self._username = ""
        self._password = ""

        title = QLabel(
            "<h3>Вход в educationDB</h3>"
            "<p>Введите логин и пароль учётной записи PostgreSQL.</p>"
        )
        title.setTextFormat(Qt.RichText)

        self.host_edit = QLineEdit(DB_HOST)
        self.port_edit = QLineEdit(str(DB_PORT))
        self.db_edit = QLineEdit(DB_NAME)
        self.user_edit = QLineEdit(DB_USER or "")
        self.pass_edit = QLineEdit()
        self.pass_edit.setEchoMode(QLineEdit.Password)
        self.show_pass = QCheckBox("Показать пароль")
        self.show_pass.toggled.connect(self._toggle_password)

        form = QFormLayout()
        form.addRow("Сервер:", self.host_edit)
        form.addRow("Порт:", self.port_edit)
        form.addRow("База данных:", self.db_edit)
        form.addRow("Логин:", self.user_edit)
        form.addRow("Пароль:", self.pass_edit)
        form.addRow("", self.show_pass)

        self.btn_ok = QPushButton("Войти")
        self.btn_ok.setDefault(True)
        self.btn_cancel = QPushButton("Отмена")
        self.btn_ok.clicked.connect(self._on_login)
        self.btn_cancel.clicked.connect(self.reject)

        buttons = QHBoxLayout()
        buttons.addStretch(1)
        buttons.addWidget(self.btn_ok)
        buttons.addWidget(self.btn_cancel)

        layout = QVBoxLayout(self)
        layout.addWidget(title)
        layout.addLayout(form)
        layout.addLayout(buttons)

        if self.user_edit.text():
            self.pass_edit.setFocus()
        else:
            self.user_edit.setFocus()

    def _toggle_password(self, checked: bool):
        self.pass_edit.setEchoMode(
            QLineEdit.Normal if checked else QLineEdit.Password
        )

    def _on_login(self):
        host = self.host_edit.text().strip()
        port_text = self.port_edit.text().strip()
        db_name = self.db_edit.text().strip()
        user = self.user_edit.text().strip()
        password = self.pass_edit.text()

        if not host or not db_name or not user:
            QMessageBox.warning(
                self, "Поля не заполнены",
                "Укажите сервер, базу данных и логин."
            )
            return
        try:
            port = int(port_text)
        except ValueError:
            QMessageBox.warning(self, "Неверный порт", "Порт должен быть числом.")
            return

        # Удаляем предыдущее тестовое соединение, если оно осталось.
        if QSqlDatabase.contains(self.CONNECTION_NAME):
            QSqlDatabase.removeDatabase(self.CONNECTION_NAME)

        probe = QSqlDatabase.addDatabase("QPSQL", self.CONNECTION_NAME)
        probe.setHostName(host)
        probe.setPort(port)
        probe.setDatabaseName(db_name)
        probe.setUserName(user)
        probe.setPassword(password)

        opened = probe.open()
        err_text = probe.lastError().text() if not opened else ""
        probe.close()
        QSqlDatabase.removeDatabase(self.CONNECTION_NAME)

        if not opened:
            QMessageBox.critical(
                self, "Ошибка авторизации",
                "PostgreSQL отклонил подключение.\n\n"
                f"{err_text}\n\n"
                "Проверьте логин/пароль и доступность сервера."
            )
            self.pass_edit.selectAll()
            self.pass_edit.setFocus()
            return

        self._host = host
        self._port = port
        self._db_name = db_name
        self._username = user
        self._password = password
        self.accept()

    @property
    def credentials(self) -> dict:
        return {
            "host": self._host,
            "port": self._port,
            "db_name": self._db_name,
            "username": self._username,
            "password": self._password,
        }
