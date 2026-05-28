"""
db_config.py — Параметры подключения к БД educationDB.

Хранит «куда подключаться» (host/port/dbname) и логин роли PostgreSQL
по умолчанию для предзаполнения поля ввода в окне авторизации.
Пароль здесь НЕ хранится: его вводит пользователь в окне входа,
а аутентификацию выполняет сам PostgreSQL (см. login_dialog.py).
"""

DB_HOST = "localhost"
DB_PORT = 5432
DB_NAME = "educationDB"
DB_USER = "postgres"  # логин по умолчанию для поля ввода
