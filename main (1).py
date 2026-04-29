#!/usr/bin/env python3
"""
main.py — Главное приложение.

Включает формы из:
    - ЛР №2 (forms_lab2):  родительские таблицы Branch_office, Product
                            в виде Details + DataGridView
    - ЛР №3 (forms_ui):    связанные таблицы (Master-Detail, M:M, VIEW)

БД: educationDB (PostgreSQL).
Стек: Python 3 + PyQt5 + QSql.

Запуск:
    python3 main.py
"""

import sys
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QAction, QMessageBox, QLabel, QMenu,
)
from PyQt5.QtSql import QSqlDatabase
from PyQt5.QtCore import Qt

from db_config import DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD

# Формы ЛР №3 (то, что уже было)
from forms_ui import (
    BranchOfficeForm, ShopForm, ProductForm,
    ShopProductForm, ShopFullInfoForm,
)

# Формы ЛР №2 (новые)
from forms_lab2 import BranchOfficeDetailsForm, ProductDetailsForm

from login_dialog import LoginDialog


# ============================================================
def authorize() -> bool:
    """Окно авторизации: сверяет введённые логин/пароль с учётной записью
    PostgreSQL из db_config.py."""
    dialog = LoginDialog()
    return dialog.exec_() == LoginDialog.Accepted


def connect_db() -> bool:
    """Подключение к PostgreSQL через QPSQL-драйвер."""
    db = QSqlDatabase.addDatabase("QPSQL")
    db.setHostName(DB_HOST)
    db.setPort(DB_PORT)
    db.setDatabaseName(DB_NAME)
    db.setUserName(DB_USER)
    db.setPassword(DB_PASSWORD)

    if not db.open():
        QMessageBox.critical(
            None,
            "Ошибка подключения к БД",
            f"Не удалось подключиться к {DB_NAME}@{DB_HOST}:{DB_PORT}\n\n"
            f"Ошибка: {db.lastError().text()}\n\n"
            f"Проверьте:\n"
            f"  1) PostgreSQL запущен (sudo systemctl status postgresql)\n"
            f"  2) БД '{DB_NAME}' существует "
            f"(psql -U postgres -f setup_db.sql)\n"
            f"  3) Логин/пароль в db_config.py"
        )
        return False
    return True


# ============================================================
class MainWindow(QMainWindow):
    """Главное окно с меню «ЛР №2», «ЛР №3» и панелью инструментов."""

    def __init__(self):
        super().__init__()
        base_title = (
            "Лабораторные работы №2 и №3 — educationDB (PyQt5 + PostgreSQL)"
        )
        self.resize(1100, 700)
        db = QSqlDatabase.database()
        user = db.userName() if db.isValid() else ""
        if user:
            self.setWindowTitle(f"{base_title} — пользователь: {user}")
            self.statusBar().showMessage(
                f"Подключено к educationDB как «{user}»", 5000
            )
        else:
            self.setWindowTitle(base_title)
            self.statusBar().showMessage("Подключено к educationDB", 5000)

        self._create_menu()
        self._create_toolbar()
        self._create_central()

    # --------------------------------------------------------
    def _create_central(self):
        central = QLabel(
            "<h2>Лабораторные работы №2 и №3</h2>"
            "<h3>educationDB — сеть магазинов с филиалами</h3>"
            "<hr>"
            "<table cellpadding='6'>"
            "<tr><td colspan='2'><b>📘 ЛР №2</b> — родительские таблицы "
            "(Details + DataGridView):</td></tr>"
            "<tr><td>📁</td><td>Филиалы — карточка + фото директора</td></tr>"
            "<tr><td>📦</td><td>Продукты — карточка + ComboBox/ListBox</td></tr>"
            "<tr><td colspan='2'><br/><b>📗 ЛР №3</b> — связанные таблицы:</td></tr>"
            "<tr><td>🏪</td><td>Магазины (Master-Detail 1:M)</td></tr>"
            "<tr><td>🛒</td><td>Товары в магазинах (M:M)</td></tr>"
            "<tr><td>📊</td><td>VIEW shop_full_info</td></tr>"
            "</table>"
        )
        central.setAlignment(Qt.AlignCenter)
        central.setStyleSheet("""
            QLabel {
                background: qlineargradient(
                    x1:0, y1:0, x2:0, y2:1,
                    stop:0 #f0f4f8, stop:1 #d9e2ec
                );
                border: 1px solid #bcccdc;
                border-radius: 8px;
                padding: 30px;
                font-size: 14px;
            }
        """)
        self.setCentralWidget(central)

    # --------------------------------------------------------
    def _create_menu(self):
        menu = self.menuBar()

        # ----- Меню «ЛР №2» (новое) -----
        lab2_menu = menu.addMenu("ЛР №2 (родительские таблицы)")

        act_branch_d = QAction("📁 Филиалы — карточка (Details)", self)
        act_branch_d.setShortcut("Ctrl+Shift+1")
        act_branch_d.setStatusTip(
            "Branch_office: Details + фото + ComboBox + DataGridView"
        )
        act_branch_d.triggered.connect(self._open_branch_details)
        lab2_menu.addAction(act_branch_d)

        act_product_d = QAction("📦 Продукты — карточка (Details)", self)
        act_product_d.setShortcut("Ctrl+Shift+2")
        act_product_d.setStatusTip(
            "Product: Details + ComboBox/ListBox + DataGridView"
        )
        act_product_d.triggered.connect(self._open_product_details)
        lab2_menu.addAction(act_product_d)

        # ----- Меню «ЛР №3» (то, что было) -----
        forms_menu = menu.addMenu("ЛР №3 (связанные таблицы)")

        act_branch = QAction("📁 Филиалы (упрощённо)", self)
        act_branch.setShortcut("Ctrl+1")
        act_branch.triggered.connect(self._open_branch)
        forms_menu.addAction(act_branch)

        act_shop = QAction("🏪 Магазины (1:M)", self)
        act_shop.setShortcut("Ctrl+2")
        act_shop.triggered.connect(self._open_shop)
        forms_menu.addAction(act_shop)

        act_product = QAction("📦 Продукты (упрощённо)", self)
        act_product.setShortcut("Ctrl+3")
        act_product.triggered.connect(self._open_product)
        forms_menu.addAction(act_product)

        act_sp = QAction("🛒 Товары в магазинах (M:M)", self)
        act_sp.setShortcut("Ctrl+4")
        act_sp.triggered.connect(self._open_shop_product)
        forms_menu.addAction(act_sp)

        forms_menu.addSeparator()

        act_view = QAction("📊 Полная информация (VIEW)", self)
        act_view.setShortcut("Ctrl+5")
        act_view.triggered.connect(self._open_view)
        forms_menu.addAction(act_view)

        forms_menu.addSeparator()
        act_quit = QAction("Выход", self)
        act_quit.setShortcut("Ctrl+Q")
        act_quit.triggered.connect(self.close)
        forms_menu.addAction(act_quit)

        # ----- Справка -----
        help_menu = menu.addMenu("Справка")
        act_about = QAction("О программе", self)
        act_about.triggered.connect(self._about)
        help_menu.addAction(act_about)

    def _create_toolbar(self):
        tb = self.addToolBar("Основное")
        tb.setMovable(False)

        items = [
            ("📁 Филиалы (карт.)",  "ЛР №2: Branch_office Details", self._open_branch_details),
            ("📦 Продукты (карт.)", "ЛР №2: Product Details",       self._open_product_details),
            None,  # разделитель
            ("📁 Филиалы",          "ЛР №3: упрощённый вид",         self._open_branch),
            ("🏪 Магазины",         "ЛР №3: Master-Detail 1:M",      self._open_shop),
            ("📦 Продукты",         "ЛР №3: упрощённый вид",         self._open_product),
            ("🛒 Товары",           "ЛР №3: M:M",                    self._open_shop_product),
            ("📊 VIEW",             "ЛР №3: представление",          self._open_view),
        ]
        for it in items:
            if it is None:
                tb.addSeparator()
                continue
            text, tip, slot = it
            act = QAction(text, self)
            act.setToolTip(tip)
            act.triggered.connect(slot)
            tb.addAction(act)

    # --------------------------------------------------------
    #  Слоты — открытие форм через Singleton
    # --------------------------------------------------------
    # ЛР №2
    def _open_branch_details(self):
        BranchOfficeDetailsForm.instance()
        self.statusBar().showMessage(
            "ЛР №2: Филиалы — Details", 3000
        )

    def _open_product_details(self):
        ProductDetailsForm.instance()
        self.statusBar().showMessage(
            "ЛР №2: Продукты — Details", 3000
        )

    # ЛР №3
    def _open_branch(self):
        BranchOfficeForm.instance()
        self.statusBar().showMessage("ЛР №3: Филиалы", 3000)

    def _open_shop(self):
        ShopForm.instance()
        self.statusBar().showMessage("ЛР №3: Магазины (Master-Detail)", 3000)

    def _open_product(self):
        ProductForm.instance()
        self.statusBar().showMessage("ЛР №3: Продукты", 3000)

    def _open_shop_product(self):
        ShopProductForm.instance()
        self.statusBar().showMessage("ЛР №3: Товары (M:M)", 3000)

    def _open_view(self):
        ShopFullInfoForm.instance()
        self.statusBar().showMessage("ЛР №3: shop_full_info", 3000)

    def contextMenuEvent(self, event):
        """Глобальное контекстное меню главного окна: список форм + «О программе»."""
        menu = QMenu(self)

        lab2 = menu.addMenu("📘 ЛР №2 (родительские таблицы)")
        lab2.addAction("📁 Филиалы — карточка (Details)",
                       self._open_branch_details)
        lab2.addAction("📦 Продукты — карточка (Details)",
                       self._open_product_details)

        lab3 = menu.addMenu("📗 ЛР №3 (связанные таблицы)")
        lab3.addAction("📁 Филиалы",                   self._open_branch)
        lab3.addAction("🏪 Магазины (Master-Detail)",  self._open_shop)
        lab3.addAction("📦 Продукты",                  self._open_product)
        lab3.addAction("🛒 Товары в магазинах (M:M)",  self._open_shop_product)
        lab3.addAction("📊 Полная информация (VIEW)",  self._open_view)

        menu.addSeparator()

        act_about = menu.addAction("ℹ️ О программе")
        act_about.triggered.connect(self._about)

        menu.exec_(event.globalPos())

    def _about(self):
        QMessageBox.about(
            self, "О программе",
            "<b>Лабораторные работы №2 и №3</b><br><br>"
            "Стек: Python 3 + PyQt5 + PostgreSQL<br><br>"
            "<b>ЛР №2:</b> родительские таблицы (Branch_office, Product) — "
            "Details-формы с PictureBox, ComboBox/ListBox, "
            "DataGridView и BindingNavigator.<br><br>"
            "<b>ЛР №3:</b> связанные таблицы — Master-Detail (1:M), "
            "M:M через промежуточную таблицу, VIEW."
        )


# ============================================================
def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    # Авторизация по учётной записи PostgreSQL из db_config.py
    if not authorize():
        sys.exit(0)

    if not connect_db():
        sys.exit(1)

    window = MainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
