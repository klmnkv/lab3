"""
db_config.py — Параметры подключения к БД educationDB.

Логин и пароль PostgreSQL также используются в окне авторизации программы:
при запуске пользователь вводит логин/пароль, программа сверяет их с
DB_USER / DB_PASSWORD ниже, и только при совпадении открывает соединение
с БД (см. login_dialog.py, main.py).
"""

DB_HOST = "localhost"
DB_PORT = 5432
DB_NAME = "educationDB"
DB_USER = "postgres"
DB_PASSWORD = "postgres"  # <-- ваш пароль PostgreSQL
