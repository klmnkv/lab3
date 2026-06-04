#!/usr/bin/env python3
"""
main.py — Главное приложение.

Включает формы из:
    - ЛР №2 (forms_lab2):  родительские таблицы Branch_office, Product
                            в виде формы Details + таблицы (QTableView)
    - ЛР №3 (forms_ui):    связанные таблицы (Master-Detail, M:M, VIEW)

БД: educationDB (PostgreSQL).
Стек: Python 3 + PyQt5 + QSql.

Запуск:
    python3 main.py
"""

import sys
from PyQt5 import uic
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QMessageBox, QMenu,
)
from PyQt5.QtSql import QSqlDatabase

# Формы ЛР №3 (то, что уже было)
from forms_ui import (
    BranchOfficeForm, ShopForm, ProductForm,
    ShopProductForm, ShopFullInfoForm,
    ui_path,
)

# Формы ЛР №2 (новые)
from forms_lab2 import BranchOfficeDetailsForm, ProductDetailsForm

from login_dialog import LoginDialog


# ============================================================
def authorize() -> bool:
    """Окно авторизации (стиль pgAdmin): сам LoginDialog открывает
    QtSql-соединение с введёнными логином/паролем. Аутентификацию
    выполняет PostgreSQL. При успехе default-соединение остаётся
    открытым для всех моделей приложения."""
    dialog = LoginDialog()
    return dialog.exec_() == LoginDialog.Accepted


# ============================================================
class MainWindow(QMainWindow):
    """Главное окно с меню «ЛР №2», «ЛР №3» и панелью инструментов."""

    def __init__(self):
        super().__init__()
        uic.loadUi(ui_path("main_window.ui"), self)

        base_title = self.windowTitle()
        db = QSqlDatabase.database()
        user = db.userName() if db.isValid() else ""
        if user:
            self.setWindowTitle(f"{base_title} — пользователь: {user}")
            self.statusBar().showMessage(
                f"Подключено к educationDB как «{user}»", 5000
            )
        else:
            self.statusBar().showMessage("Подключено к educationDB", 5000)

        self._wire_actions()

    # --------------------------------------------------------
    def _wire_actions(self):
        """Подключить QAction'ы из main_window.ui к слотам."""
        wiring = [
            # Меню
            (self.actBranchDetails,   self._open_branch_details),
            (self.actProductDetails,  self._open_product_details),
            (self.actBranchSimple,    self._open_branch),
            (self.actShop,            self._open_shop),
            (self.actProductSimple,   self._open_product),
            (self.actShopProduct,     self._open_shop_product),
            (self.actView,            self._open_view),
            (self.actQuit,            self.close),
            (self.actAbout,           self._about),
            # Тулбар
            (self.actTbBranchDetails, self._open_branch_details),
            (self.actTbProductDetails, self._open_product_details),
            (self.actTbBranch,        self._open_branch),
            (self.actTbShop,          self._open_shop),
            (self.actTbProduct,       self._open_product),
            (self.actTbShopProduct,   self._open_shop_product),
            (self.actTbView,          self._open_view),
        ]
        for action, slot in wiring:
            action.triggered.connect(slot)

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
            "Details-формы с полем для изображения (QLabel + QPixmap), "
            "ComboBox/QListWidget, QTableView и панелью навигации.<br><br>"
            "<b>ЛР №3:</b> связанные таблицы — Master-Detail (1:M), "
            "M:M через промежуточную таблицу, VIEW."
        )


# ============================================================
def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    # Авторизация = подключение к БД через LoginDialog (стиль pgAdmin)
    if not authorize():
        sys.exit(0)

    window = MainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
