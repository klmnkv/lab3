"""
login_dialog.py — Диалог авторизации.

Пользователь вводит логин и пароль. Введённые значения сравниваются с
учётными данными PostgreSQL из db_config.py (DB_USER / DB_PASSWORD).
Если совпали — авторизация пройдена; основное соединение с БД затем
открывает main.py этими же кредами.
"""

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QDialog, QLabel, QLineEdit, QPushButton,
    QVBoxLayout, QFormLayout, QHBoxLayout, QMessageBox, QCheckBox
)

from db_config import DB_USER, DB_PASSWORD


class LoginDialog(QDialog):
    """Диалог ввода логина/пароля учётной записи PostgreSQL."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Авторизация — educationDB")
        self.setModal(True)
        self.setMinimumWidth(340)

        title = QLabel(
            "<h3>Вход в программу</h3>"
            "<p>Введите логин и пароль учётной записи PostgreSQL.</p>"
        )
        title.setTextFormat(Qt.RichText)

        self.user_edit = QLineEdit()
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

        self.user_edit.setFocus()

    def _toggle_password(self, checked: bool):
        self.pass_edit.setEchoMode(
            QLineEdit.Normal if checked else QLineEdit.Password
        )

    def _on_login(self):
        user = self.user_edit.text().strip()
        password = self.pass_edit.text()

        if not user or not password:
            QMessageBox.warning(
                self, "Поля не заполнены",
                "Введите логин и пароль."
            )
            return

        if user != DB_USER or password != DB_PASSWORD:
            QMessageBox.critical(
                self, "Ошибка авторизации",
                "Неверный логин или пароль учётной записи PostgreSQL."
            )
            self.pass_edit.selectAll()
            self.pass_edit.setFocus()
            return

        self.accept()
