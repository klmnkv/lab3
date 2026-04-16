# Лабораторная работа №3 — PyQt5 + PostgreSQL (educationDB)

## Структура проекта

```
project/
├── setup_db.sql     — SQL-скрипт создания БД и тестовых данных
├── db_config.py     — Настройки подключения к PostgreSQL
├── main.py          — Точка входа: главное окно + подключение к БД
├── forms.py         — Все формы приложения
└── README.md        — Этот файл
```

## Установка и запуск

### 1. Установить зависимости

```bash
# PostgreSQL
sudo apt install postgresql postgresql-client pgadmin4-desktop

# Python-пакеты
pip install PyQt5 psycopg2-binary

# Qt-плагин для PostgreSQL (если не установлен)
sudo apt install libqt5sql5-psql
```

### 2. Создать базу данных

```bash
sudo -u postgres psql -f setup_db.sql
```

Или если используется пароль:
```bash
psql -U postgres -f setup_db.sql
```

### 3. Настроить подключение

Отредактируйте `db_config.py`:
```python
DB_HOST = "localhost"
DB_PORT = 5432
DB_NAME = "educationDB"
DB_USER = "postgres"
DB_PASSWORD = "ваш_пароль"
```

### 4. Запустить приложение

```bash
python3 main.py
```

## Реализованные задания

| № | Задание | Реализация |
|---|---------|------------|
| 1 | Подключение к educationDB | `main.py → connect_db()` |
| 2 | Главная форма с меню | `MainWindow` + QMenuBar + QToolBar |
| 3 | Singleton для форм | `@classmethod instance()` в каждой форме |
| 4 | 1:M Branch_office → Shop | `ShopForm` (master-detail, splitter) |
| 5 | M:M Product ↔ Shop | `ShopProductForm` через Shop_Product |
| 6 | Обработка исключений | `model.submitAll()` + QMessageBox |
| 7 | Поиск и фильтрация | `SearchPanel` + `model.setFilter()` |
| 8 | Вычисляемые колонки | `GENERATED` в БД + VIEW shop_full_info |
| 9 | Подстановочные поля | `QSqlRelationalTableModel` + `QSqlRelation` |
| 10 | Кнопка выбора филиала | `BranchSelectDialog` (QDialog) |
| 11 | Навигация (BindingNavigator) | `NavigationToolbar` (QToolBar) |
| 12 | Тестирование CRUD | Встроено во все формы |

## Архитектура

```
MainWindow (QMainWindow)
├── Меню «Формы» → открытие форм через Singleton
├── Панель инструментов → быстрый доступ к формам
│
├── BranchOfficeForm    — Филиалы (CRUD + поиск)
├── ProductForm         — Продукты (CRUD + поиск)
├── ShopForm            — Master-Detail: Филиал → Магазины
│   ├── master: QTableView (Branch_office)
│   ├── detail: QTableView (Shop) + QSqlRelationalTableModel
│   └── BranchSelectDialog (кнопка выбора филиала)
├── ShopProductForm     — M:M: Магазин → Товары
│   ├── master: QTableView (Shop)
│   └── detail: QTableView (Shop_Product) + Lookup
└── ShopFullInfoForm    — VIEW shop_full_info (только чтение)
```

## Соответствие Windows Forms → PyQt5

| Windows Forms | PyQt5 |
|--------------|-------|
| DataGridView + BindingSource | QTableView + QSqlTableModel |
| DataColumn.Expression | PostgreSQL GENERATED / VIEW |
| Parent(FK).Field | QSqlRelationalTableModel + QSqlRelation |
| BindingNavigator | NavigationToolbar (QToolBar + QAction) |
| BindingSource.Filter | QSqlTableModel.setFilter() |
| static Form | @classmethod + _instance (Singleton) |
