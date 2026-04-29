#!/usr/bin/env python3
"""
main.py — Главное приложение для лабораторной работы №3.
БД: educationDB (PostgreSQL)
Стек: Python 3 + PyQt5 + QSql

Запуск:
    python3 main.py

Перед запуском:
    1) psql -U postgres -f setup_db.sql
    2) pip install PyQt5 psycopg2-binary
    3) Проверьте db_config.py (логин/пароль PostgreSQL)
"""

import sys
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QAction, QMenuBar, QToolBar,
    QMessageBox, QStatusBar, QLabel, QMdiArea, QMdiSubWindow, QMenu
)
from PyQt5.QtSql import QSqlDatabase
from PyQt5.QtCore import Qt

from forms import (
    BranchOfficeForm, ShopForm, ProductForm,
    ShopProductForm, ShopFullInfoForm
)
from login_dialog import LoginDialog


def connect_db() -> bool:
    """Авторизация через PostgreSQL: учётные данные вводит пользователь.

    Показываем диалог логина — он сам проверяет креды, открывая пробное
    соединение. Если диалог принят, открываем основное соединение
    приложения с теми же параметрами.
    """
    dialog = LoginDialog()
    if dialog.exec_() != LoginDialog.Accepted:
        return False

    creds = dialog.credentials
    db = QSqlDatabase.addDatabase("QPSQL")
    db.setHostName(creds["host"])
    db.setPort(creds["port"])
    db.setDatabaseName(creds["db_name"])
    db.setUserName(creds["username"])
    db.setPassword(creds["password"])

    if not db.open():
        QMessageBox.critical(
            None,
            "Ошибка подключения к БД",
            "Не удалось открыть основное соединение после авторизации.\n\n"
            f"Ошибка: {db.lastError().text()}"
        )
        return False
    return True


class MainWindow(QMainWindow):
    """Главное окно приложения с меню и панелью инструментов."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Лабораторная №3 — educationDB (PyQt5 + PostgreSQL)")
        self.resize(1100, 700)
        db = QSqlDatabase.database()
        user = db.userName() if db.isValid() else ""
        if user:
            self.statusBar().showMessage(
                f"Подключено к educationDB как «{user}»", 5000
            )
            self.setWindowTitle(
                f"Лабораторная №3 — educationDB (PyQt5 + PostgreSQL) — "
                f"пользователь: {user}"
            )
        else:
            self.statusBar().showMessage("Подключено к educationDB", 5000)

        self._create_menu()
        self._create_toolbar()

        # Центральная область — информационный виджет
        central = QLabel(
            "<h2>Лабораторная работа №3</h2>"
            "<h3>Создание приложения на PyQt5 для работы "
            "со связанными таблицами БД educationDB</h3>"
            "<br>"
            "<p><b>Предметная область:</b> сеть магазинов с филиалами</p>"
            "<p><b>Таблицы:</b> Branch_office, Shop, Product, Shop_Product</p>"
            "<hr>"
            "<p>Выберите форму из меню <b>«Формы»</b> или "
            "панели инструментов.</p>"
            "<br>"
            "<table cellpadding='4'>"
            "<tr><td>📁</td><td><b>Филиалы</b> — справочник филиалов</td></tr>"
            "<tr><td>🏪</td><td><b>Магазины</b> — master-detail "
            "(Branch_office → Shop)</td></tr>"
            "<tr><td>📦</td><td><b>Продукты</b> — справочник продуктов</td></tr>"
            "<tr><td>🛒</td><td><b>Товары в магазинах</b> — M:M "
            "(Product ↔ Shop)</td></tr>"
            "<tr><td>📊</td><td><b>Полная информация</b> — VIEW "
            "с вычисляемыми колонками</td></tr>"
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

    def _create_menu(self):
        menu = self.menuBar()

        # Меню «Формы»
        forms_menu = menu.addMenu("Формы")

        act_branch = QAction("📁 Филиалы", self)
        act_branch.setShortcut("Ctrl+1")
        act_branch.setStatusTip("Открыть справочник филиалов")
        act_branch.triggered.connect(self._open_branch)
        forms_menu.addAction(act_branch)

        act_shop = QAction("🏪 Магазины (1:M)", self)
        act_shop.setShortcut("Ctrl+2")
        act_shop.setStatusTip(
            "Master-Detail: филиал → магазины + выбор филиала из справочника"
        )
        act_shop.triggered.connect(self._open_shop)
        forms_menu.addAction(act_shop)

        act_product = QAction("📦 Продукты", self)
        act_product.setShortcut("Ctrl+3")
        act_product.setStatusTip("Открыть справочник продуктов")
        act_product.triggered.connect(self._open_product)
        forms_menu.addAction(act_product)

        act_sp = QAction("🛒 Товары в магазинах (M:M)", self)
        act_sp.setShortcut("Ctrl+4")
        act_sp.setStatusTip(
            "Связь M:M через Shop_Product + Lookup + вычисляемая выручка"
        )
        act_sp.triggered.connect(self._open_shop_product)
        forms_menu.addAction(act_sp)

        forms_menu.addSeparator()

        act_view = QAction("📊 Полная информация (VIEW)", self)
        act_view.setShortcut("Ctrl+5")
        act_view.setStatusTip(
            "Представление shop_full_info с вычисляемыми колонками"
        )
        act_view.triggered.connect(self._open_view)
        forms_menu.addAction(act_view)

        forms_menu.addSeparator()

        act_quit = QAction("Выход", self)
        act_quit.setShortcut("Ctrl+Q")
        act_quit.triggered.connect(self.close)
        forms_menu.addAction(act_quit)

        # Меню «Справка»
        help_menu = menu.addMenu("Справка")
        act_about = QAction("О программе", self)
        act_about.triggered.connect(self._about)
        help_menu.addAction(act_about)

    def _create_toolbar(self):
        tb = self.addToolBar("Основное")
        tb.setMovable(False)

        for text, tip, slot in [
            ("📁 Филиалы", "Справочник филиалов", self._open_branch),
            ("🏪 Магазины", "Master-Detail: Филиал→Магазины", self._open_shop),
            ("📦 Продукты", "Справочник продуктов", self._open_product),
            ("🛒 Товары", "M:M: Товары в магазинах", self._open_shop_product),
            ("📊 VIEW", "Представление shop_full_info", self._open_view),
        ]:
            act = QAction(text, self)
            act.setToolTip(tip)
            act.triggered.connect(slot)
            tb.addAction(act)

    # --- Открытие форм (Singleton) ---
    def _open_branch(self):
        BranchOfficeForm.instance()
        self.statusBar().showMessage("Открыта форма: Филиалы", 3000)

    def _open_shop(self):
        ShopForm.instance()
        self.statusBar().showMessage(
            "Открыта форма: Магазины (Master-Detail)", 3000
        )

    def _open_product(self):
        ProductForm.instance()
        self.statusBar().showMessage("Открыта форма: Продукты", 3000)

    def _open_shop_product(self):
        ShopProductForm.instance()
        self.statusBar().showMessage(
            "Открыта форма: Товары в магазинах (M:M)", 3000
        )

    def _open_view(self):
        ShopFullInfoForm.instance()
        self.statusBar().showMessage("Открыта форма: VIEW shop_full_info", 3000)

    def contextMenuEvent(self, event):
        """Глобальное контекстное меню главного окна: список форм + «О программе»."""
        menu = QMenu(self)

        act_branch = menu.addAction("📁 Филиалы")
        act_branch.triggered.connect(self._open_branch)

        act_shop = menu.addAction("🏪 Магазины (Master-Detail)")
        act_shop.triggered.connect(self._open_shop)

        act_product = menu.addAction("📦 Продукты")
        act_product.triggered.connect(self._open_product)

        act_sp = menu.addAction("🛒 Товары в магазинах (M:M)")
        act_sp.triggered.connect(self._open_shop_product)

        act_view = menu.addAction("📊 Полная информация (VIEW)")
        act_view.triggered.connect(self._open_view)

        menu.addSeparator()

        act_about = menu.addAction("ℹ️ О программе")
        act_about.triggered.connect(self._about)

        menu.exec_(event.globalPos())

    def _about(self):
        QMessageBox.about(
            self,
            "О программе",
            "<b>Лабораторная работа №3</b><br><br>"
            "Создание приложения на PyQt5 для работы со связанными "
            "таблицами БД educationDB (PostgreSQL).<br><br>"
            "<b>Стек:</b> Python 3 + PyQt5 + PostgreSQL<br>"
            "<b>Реализовано:</b><br>"
            "• Master-Detail (1:M): Branch_office → Shop<br>"
            "• M:M: Product ↔ Shop через Shop_Product<br>"
            "• Singleton для форм<br>"
            "• Подстановочные поля (Lookup)<br>"
            "• Вычисляемые колонки (GENERATED + VIEW)<br>"
            "• Поиск и фильтрация<br>"
            "• Навигация (аналог BindingNavigator)<br>"
            "• Обработка ошибок CRUD<br>"
            "• Диалог выбора филиала"
        )


# ============================================================
#  Точка входа
# ============================================================
def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    # Подключение к БД
    if not connect_db():
        sys.exit(1)

    window = MainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
