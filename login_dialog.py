"""
login_dialog.py — Диалог авторизации (стиль pgAdmin).

Пользователь вводит логин и пароль; диалог САМ пытается открыть
QSqlDatabase-соединение (драйвер QPSQL) с host/port/dbname из db_config.py
и введёнными кредами. Аутентификацию выполняет сам PostgreSQL (роли).
При успехе соединение остаётся открытым и глобальным (default connection)
для всех моделей; при ошибке окно не закрывается — можно ввести заново.
"""

from PyQt5.QtCore import Qt
from PyQt5.QtSql import QSqlDatabase
from PyQt5.QtWidgets import (
    QDialog, QLabel, QLineEdit, QPushButton,
    QVBoxLayout, QFormLayout, QHBoxLayout, QMessageBox, QCheckBox
)

from db_config import DB_HOST, DB_PORT, DB_NAME, DB_USER


class LoginDialog(QDialog):
    """Диалог ввода логина/пароля учётной записи PostgreSQL."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(
            f"Авторизация — {DB_NAME} на {DB_HOST}:{DB_PORT}"
        )
        self.setModal(True)
        self.setMinimumWidth(340)

        title = QLabel(
            "<h3>Вход в программу</h3>"
            f"<p>Подключение к <b>{DB_NAME}</b> на "
            f"<b>{DB_HOST}:{DB_PORT}</b>.<br>"
            "Введите логин и пароль роли PostgreSQL.</p>"
        )
        title.setTextFormat(Qt.RichText)

        self.user_edit = QLineEdit()
        self.user_edit.setText(DB_USER)
        self.pass_edit = QLineEdit()
        self.pass_edit.setEchoMode(QLineEdit.Password)
        self.show_pass = QCheckBox("Показать пароль")
        self.show_pass.toggled.connect(self._toggle_password)

        form = QFormLayout()
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

        self.pass_edit.setFocus()

    def _toggle_password(self, checked: bool):
        self.pass_edit.setEchoMode(
            QLineEdit.Normal if checked else QLineEdit.Password
        )

    def _try_connect(self, user: str, password: str) -> bool:
        """Пытается открыть default-соединение QtSql с заданными кредами.

        Если соединение уже зарегистрировано — переиспользует его (чтобы Qt
        не ругался на дубликат при повторных попытках входа). При ошибке
        показывает critical-сообщение с текстом lastError().
        """
        if QSqlDatabase.contains():
            db = QSqlDatabase.database(
                QSqlDatabase.defaultConnection, open=False
            )
            if db.isOpen():
                db.close()
        else:
            db = QSqlDatabase.addDatabase("QPSQL")

        db.setHostName(DB_HOST)
        db.setPort(DB_PORT)
        db.setDatabaseName(DB_NAME)
        db.setUserName(user)
        db.setPassword(password)

        if not db.open():
            QMessageBox.critical(
                self,
                "Ошибка подключения к БД",
                f"Не удалось подключиться к {DB_NAME}@{DB_HOST}:{DB_PORT}\n\n"
                f"{db.lastError().text()}"
            )
            return False
        return True

    def _on_login(self):
        user = self.user_edit.text().strip()
        password = self.pass_edit.text()

        if not user:
            QMessageBox.warning(
                self, "Поле не заполнено",
                "Введите логин."
            )
            self.user_edit.setFocus()
            return

        if not self._try_connect(user, password):
            self.pass_edit.clear()
            self.pass_edit.setFocus()
            return

        self.accept()
