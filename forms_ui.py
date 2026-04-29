"""
forms_ui.py — Формы приложения ЛР №3, загружаемые из .ui файлов
(Qt Designer).

Все .ui файлы должны лежать в папке ui/ рядом с этим модулем.
"""

import os
from PyQt5 import uic
from PyQt5.QtWidgets import (
    QWidget, QTableView, QMessageBox, QDialog, QAbstractItemView
)
from PyQt5.QtSql import (
    QSqlTableModel, QSqlRelationalTableModel, QSqlRelation,
    QSqlRelationalDelegate, QSqlQuery
)
from PyQt5.QtCore import Qt, QDate

from widget import (
    NavigationToolbar, ReadOnlyDelegate, MoneyDelegate, LookupComboDelegate
)

# Путь к папке с .ui файлами
UI_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ui")


def ui_path(filename):
    return os.path.join(UI_DIR, filename)


# ============================================================
#  Столбцы для поиска (имя в ComboBox → имя колонки в БД)
# ============================================================
BRANCH_SEARCH_COLS = {
    "Название": "name", "Регион": "region",
    "Населённый пункт": "locality", "Адрес": "address",
    "Директор": "director's name"
}

PRODUCT_SEARCH_COLS = {
    "Категория": "category",
    "Название": "name",
    "Ед. изм.": "units",
}

SHOP_SEARCH_COLS = {
    "Название": "name", "Нас.пункт": "locality", "Улица": "street"
}


# ============================================================
#  Вспомогательные функции
# ============================================================
def _connect_search(widget, model, col_map):
    """Подключить виджеты поиска (searchInput, comboColumn, btnFind, btnReset)
    к фильтрации модели."""

    def apply_filter():
        val = widget.searchInput.text().strip()
        combo_text = widget.comboColumn.currentText()
        col = col_map.get(combo_text, "name")
        base = getattr(widget, "_base_filter", "").strip()
        parts = [base] if base else []
        if val:
            parts.append(f"\"{col}\"::text ILIKE '%{val}%'")
        model.setFilter(" AND ".join(parts))
        model.select()

    def reset_filter():
        widget.searchInput.clear()
        model.setFilter(getattr(widget, "_base_filter", "").strip())
        model.select()

    widget.btnFind.clicked.connect(apply_filter)
    widget.searchInput.returnPressed.connect(apply_filter)
    widget.btnReset.clicked.connect(reset_filter)


# ============================================================
#  1. Форма «Филиалы» (Branch_office) — Singleton
# ============================================================
class BranchOfficeForm(QWidget):
    _instance = None

    @classmethod
    def instance(cls):
        if cls._instance is None or not cls._instance.isVisible():
            cls._instance = cls()
        cls._instance.show()
        cls._instance.activateWindow()
        return cls._instance

    def __init__(self):
        super().__init__()
        uic.loadUi(ui_path("branch_office_form.ui"), self)

        # Модель
        self.model = QSqlTableModel()
        self.model.setTable('"Branch_office"')
        self.model.setEditStrategy(QSqlTableModel.OnManualSubmit)
        self.model.select()

        headers = {
            0: "№", 1: "Название", 2: "Регион", 3: "Населённый пункт",
            4: "Адрес", 5: "Дата открытия", 6: "Телефон",
            7: "Директор", 8: "Фото"
        }
        for col, name in headers.items():
            self.model.setHeaderData(col, Qt.Horizontal, name)

        self.tableView.setModel(self.model)
        self.tableView.setColumnHidden(8, True)
        self.tableView.horizontalHeader().setStretchLastSection(True)

        # Навигация
        self.navbar = NavigationToolbar(self.tableView, self.model, self)
        self.layout().insertWidget(0, self.navbar)

        # Поиск
        _connect_search(self, self.model, BRANCH_SEARCH_COLS)


# ============================================================
#  2. Форма «Продукты» (Product) — Singleton
# ============================================================
class ProductForm(QWidget):
    _instance = None

    @classmethod
    def instance(cls):
        if cls._instance is None or not cls._instance.isVisible():
            cls._instance = cls()
        cls._instance.show()
        cls._instance.activateWindow()
        return cls._instance

    def __init__(self):
        super().__init__()
        uic.loadUi(ui_path("product_form.ui"), self)

        self.model = QSqlTableModel()
        self.model.setTable('"Product"')
        self.model.setEditStrategy(QSqlTableModel.OnManualSubmit)
        self.model.select()

        self.model.setHeaderData(0, Qt.Horizontal, "№")
        self.model.setHeaderData(1, Qt.Horizontal, "Категория")
        self.model.setHeaderData(2, Qt.Horizontal, "Ед. изм.")
        self.model.setHeaderData(3, Qt.Horizontal, "Название")

        self.tableView.setModel(self.model)
        self.tableView.horizontalHeader().setStretchLastSection(True)

        self.navbar = NavigationToolbar(self.tableView, self.model, self)
        self.layout().insertWidget(0, self.navbar)

        _connect_search(self, self.model, PRODUCT_SEARCH_COLS)


# ============================================================
#  3. Диалог выбора филиала
# ============================================================
class BranchSelectDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        uic.loadUi(ui_path("branch_select_dialog.ui"), self)
        self.selected_id = None
        self.selected_name = None

        self.model = QSqlTableModel()
        self.model.setTable('"Branch_office"')
        self.model.select()

        self.tableView.setModel(self.model)
        self.tableView.setColumnHidden(8, True)
        self.tableView.horizontalHeader().setStretchLastSection(True)

        self.btnSelect.clicked.connect(self._accept)
        self.tableView.doubleClicked.connect(self._accept)

    def _accept(self):
        row = self.tableView.currentIndex().row()
        if row >= 0:
            self.selected_id = self.model.record(row).value("number")
            self.selected_name = self.model.record(row).value("name")
            self.accept()
        else:
            QMessageBox.warning(self, "Внимание", "Выберите филиал!")


# ============================================================
#  4. Форма «Магазины» — Master-Detail + Lookup
# ============================================================
class ShopForm(QWidget):
    _instance = None

    @classmethod
    def instance(cls):
        if cls._instance is None or not cls._instance.isVisible():
            cls._instance = cls()
        cls._instance.show()
        cls._instance.activateWindow()
        return cls._instance

    def __init__(self):
        super().__init__()
        uic.loadUi(ui_path("shop_form.ui"), self)

        # --- Master: Branch_office ---
        self.master_model = QSqlTableModel()
        self.master_model.setTable('"Branch_office"')
        self.master_model.select()

        headers_m = {0: "№", 1: "Название", 2: "Регион", 3: "Нас.пункт",
                     4: "Адрес", 5: "Дата откр.", 6: "Телефон", 7: "Директор"}
        for c, n in headers_m.items():
            self.master_model.setHeaderData(c, Qt.Horizontal, n)

        self.masterView.setModel(self.master_model)
        self.masterView.setColumnHidden(8, True)
        self.masterView.horizontalHeader().setStretchLastSection(True)
        self.masterView.selectionModel().currentRowChanged.connect(
            self._on_master_changed
        )

        # --- Detail: Shop с Lookup ---
        self.detail_model = QSqlRelationalTableModel()
        self.detail_model.setTable('"Shop"')
        self.detail_model.setEditStrategy(QSqlTableModel.OnManualSubmit)
        self.detail_model.setRelation(
            8, QSqlRelation('"Branch_office"', 'number', 'name')
        )
        self.detail_model.select()

        # Автоподстановка number_office при добавлении новой строки в Shop
        self.detail_model.rowsInserted.connect(self._autofill_office_on_insert)
        # Надёжная подстановка FK непосредственно в QSqlRecord перед INSERT.
        self.detail_model.primeInsert.connect(self._prime_shop_insert)

        headers_d = {0: "№", 1: "Название", 2: "Нас.пункт", 3: "Улица",
                     4: "Дом", 5: "Телефон", 6: "Открыт", 7: "Дата откр.",
                     8: "Филиал"}
        for c, n in headers_d.items():
            self.detail_model.setHeaderData(c, Qt.Horizontal, n)

        self.detailView.setModel(self.detail_model)
        self.detailView.setItemDelegate(
            QSqlRelationalDelegate(self.detailView)
        )
        self.detailView.horizontalHeader().setStretchLastSection(True)

        # Навигация для detail
        self.navbar = NavigationToolbar(
            self.detailView, self.detail_model, self
        )
        # Вставить в detailLayout (внутри groupDetail)
        self.groupDetail.layout().insertWidget(0, self.navbar)
        self.navbar.row_inserted.connect(self._on_detail_row_inserted)

        # Поиск
        _connect_search(self, self.detail_model, SHOP_SEARCH_COLS)

        # Кнопка выбора филиала
        self.btnSelectBranch.clicked.connect(self._select_branch)

        # Выбрать первый филиал
        if self.master_model.rowCount() > 0:
            self.masterView.selectRow(0)

    def _autofill_office_on_insert(self, parent, first, last):
        """При добавлении новой строки в detail-таблицу Shop
        автоматически подставить number_office из выбранного
        в master-таблице филиала.

        Важно: колонка 8 — relation в QSqlRelationalTableModel.
        setData на relation-колонке ожидает DISPLAY-значение
        (название филиала), по нему Qt находит FK во внутреннем
        dictionary. Передача сырого id числом приводит к
        молчаливому false и row уходит в INSERT с NULL."""
        current = self.masterView.currentIndex()
        if not current.isValid():
            return
        master_rec = self.master_model.record(current.row())
        office_id = master_rec.value("number")
        office_name = master_rec.value("name")
        if office_id in (None, "", 0) or not office_name:
            return

        # Подстраховка: relation-model для FK может быть ещё пустой,
        # тогда setData(display-value) вернёт False.
        rel_model = self.detail_model.relationModel(8)
        if rel_model is not None:
            rel_model.select()

        for row in range(first, last + 1):
            rec = self.detail_model.record(row)
            # Relation column — сначала пишем DISPLAY-значение
            # (имя филиала), чтобы Qt сам резолвил FK.
            ok = self.detail_model.setData(
                self.detail_model.index(row, 8),
                office_name, Qt.EditRole
            )
            # Если relation dictionary ещё не готов — пишем FK напрямую.
            if not ok:
                rec.setValue("number_office", office_id)
                self.detail_model.setRecord(row, rec)
            if rec.isNull("openning_date"):
                self.detail_model.setData(
                    self.detail_model.index(row, 7),
                    QDate.currentDate(),
                    Qt.EditRole
                )

    def _prime_shop_insert(self, *args):
        """Перед фактическим INSERT гарантированно проставить FK филиала.

        В PyQt сигнал primeInsert может приходить как:
          - primeInsert(QSqlRecord)
          - primeInsert(int, QSqlRecord)
        Поэтому извлекаем QSqlRecord из args безопасно.
        """
        if not args:
            return
        record = args[-1]
        if not hasattr(record, "indexOf"):
            return
        current = self.masterView.currentIndex()
        if not current.isValid():
            return
        office_id = self.master_model.record(current.row()).value("number")
        if office_id in (None, "", 0):
            return
        idx_fk = record.indexOf("number_office")
        if idx_fk >= 0:
            record.setValue(idx_fk, office_id)
        idx_date = record.indexOf("openning_date")
        if idx_date >= 0 and record.isNull(idx_date):
            record.setValue(idx_date, QDate.currentDate())

    def _on_detail_row_inserted(self, row: int):
        """Страховка для вставки через NavigationToolbar.➕"""
        current = self.masterView.currentIndex()
        if not current.isValid():
            return
        master_rec = self.master_model.record(current.row())
        office_id = master_rec.value("number")
        office_name = master_rec.value("name")
        if office_id in (None, "", 0):
            return
        # Для relation-колонки пробуем сначала RAW FK, затем display name.
        ok = self.detail_model.setData(
            self.detail_model.index(row, 8), office_id, Qt.EditRole
        )
        if not ok and office_name:
            self.detail_model.setData(
                self.detail_model.index(row, 8), office_name, Qt.EditRole
            )
        rec = self.detail_model.record(row)
        if rec.isNull("openning_date"):
            self.detail_model.setData(
                self.detail_model.index(row, 7),
                QDate.currentDate(),
                Qt.EditRole
            )

    def _on_master_changed(self, current, previous):
        if not current.isValid():
            return
        office_id = self.master_model.record(current.row()).value("number")
        self._base_filter = f'number_office = {office_id}'
        val = self.searchInput.text().strip()
        if val:
            col = SHOP_SEARCH_COLS.get(self.comboColumn.currentText(), "name")
            self.detail_model.setFilter(
                f"{self._base_filter} AND \"{col}\"::text ILIKE '%{val}%'"
            )
        else:
            self.detail_model.setFilter(self._base_filter)
        self.detail_model.select()
        self.labelStatus.setText(
            f"Филиал №{office_id} — показано магазинов: "
            f"{self.detail_model.rowCount()}"
        )

    def _select_branch(self):
        dlg = BranchSelectDialog(self)
        if dlg.exec_() != QDialog.Accepted or dlg.selected_id is None:
            return

        row = self.detailView.currentIndex().row()
        if row < 0:
            QMessageBox.warning(
                self, "Внимание",
                "Сначала выберите магазин в нижней таблице."
            )
            return

        # Сохранить PK магазина ДО снятия фильтра
        shop_id = self.detail_model.record(row).value("number")

        self.detail_model.setFilter("")
        self.detail_model.select()

        # Найти целевую строку по PK, а не по старому индексу
        target_row = -1
        for r in range(self.detail_model.rowCount()):
            if self.detail_model.record(r).value("number") == shop_id:
                target_row = r
                break
        if target_row < 0:
            QMessageBox.warning(
                self, "Ошибка",
                "Не удалось найти магазин после перезагрузки."
            )
            return

        # Relation column — пишем DISPLAY-значение (имя филиала),
        # по нему Qt найдёт FK в dictionary.
        self.detail_model.setData(
            self.detail_model.index(target_row, 8),
            dlg.selected_name, Qt.EditRole
        )

        if not self.detail_model.submitAll():
            QMessageBox.critical(
                self, "Ошибка",
                self.detail_model.lastError().text()
            )
            self.detail_model.revertAll()
        else:
            QMessageBox.information(
                self, "Готово",
                f"Магазину назначен филиал «{dlg.selected_name}» "
                f"(id={dlg.selected_id})."
            )

        # Обновить обе таблицы
        self.master_model.select()
        if self.masterView.currentIndex().isValid():
            self._on_master_changed(self.masterView.currentIndex(), None)


# ============================================================
#  5. Форма «Товары в магазинах» (M:M)
# ============================================================
class ShopProductForm(QWidget):
    _instance = None

    @classmethod
    def instance(cls):
        if cls._instance is None or not cls._instance.isVisible():
            cls._instance = cls()
        cls._instance.show()
        cls._instance.activateWindow()
        return cls._instance

    def __init__(self):
        super().__init__()
        uic.loadUi(ui_path("shop_product_form.ui"), self)

        # --- Master: Shop ---
        self.shop_model = QSqlTableModel()
        self.shop_model.setTable('"Shop"')
        self.shop_model.select()

        shop_headers = {0: "№", 1: "Название", 2: "Нас.пункт", 3: "Улица",
                        4: "Дом", 5: "Телефон", 6: "Открыт", 7: "Дата откр.",
                        8: "Филиал (id)"}
        for c, n in shop_headers.items():
            self.shop_model.setHeaderData(c, Qt.Horizontal, n)

        self.shopView.setModel(self.shop_model)
        self.shopView.horizontalHeader().setStretchLastSection(True)
        self.shopView.selectionModel().currentRowChanged.connect(
            self._on_shop_changed
        )

        # --- Detail: Shop_Product (плоская модель) ---
        # QSqlRelationalTableModel не годится: num_product входит в
        # составной PK, и при setRelation(0, ...) Qt ломает WHERE-клаузу
        # для UPDATE/DELETE (алиас JOIN подставляется вместо имени
        # колонки). Симптомы — цена не сохраняется, строки не удаляются,
        # ошибок при этом может не быть (UPDATE обновляет 0 строк).
        # Поэтому берём QSqlTableModel и делаем подстановку имени товара
        # кастомным LookupComboDelegate'ом.
        self.sp_model = QSqlTableModel()
        self.sp_model.setTable('"Shop_Product"')
        self.sp_model.setEditStrategy(QSqlTableModel.OnManualSubmit)
        self.sp_model.select()

        # Автоподстановка num_shop при добавлении новой строки в Shop_Product
        self.sp_model.rowsInserted.connect(self._autofill_shop_on_insert)

        sp_headers = {0: "Продукт", 1: "Магазин (id)", 2: "Кол-во",
                      3: "Цена за ед.", 4: "Выручка (авто)"}
        for c, n in sp_headers.items():
            self.sp_model.setHeaderData(c, Qt.Horizontal, n)

        self._products = self._load_products()
        self._product_label_to_id = {n: i for i, n in self._products}

        self.spView.setModel(self.sp_model)
        self.spView.setItemDelegateForColumn(
            0, LookupComboDelegate(self._products, self.spView)
        )
        self.spView.setItemDelegateForColumn(3, MoneyDelegate(self.spView))
        self.spView.horizontalHeader().setStretchLastSection(True)

        # Запретить редактирование вычисляемой колонки
        self.spView.setItemDelegateForColumn(4, ReadOnlyDelegate(self.spView))

        # Навигация
        self.navbar = NavigationToolbar(self.spView, self.sp_model, self)
        self.groupProducts.layout().insertWidget(0, self.navbar)

        if self.shop_model.rowCount() > 0:
            self.shopView.selectRow(0)

    def _load_products(self):
        """Загрузить справочник продуктов [(id, label), ...] один раз.
        label = «категория» или «категория — название», если name задан."""
        items = []
        q = QSqlQuery()
        if q.exec_(
            'SELECT number, category, name FROM "Product" ORDER BY number'
        ):
            while q.next():
                pid = int(q.value(0))
                category = str(q.value(1) or "").strip()
                name = str(q.value(2) or "").strip()
                label = f"{category} — {name}" if name else category
                items.append((pid, label))
        return items

    def _autofill_shop_on_insert(self, parent, first, last):
        """При добавлении новой строки в Shop_Product автоматически
        подставить num_shop из выбранного магазина и свободный
        num_product из справочника. Модель — плоский QSqlTableModel,
        поэтому пишем сырые int id в обе колонки."""
        current = self.shopView.currentIndex()
        if not current.isValid():
            return
        shop_id = self.shop_model.record(current.row()).value("number")
        if shop_id in (None, "", 0):
            return
        used_products = set()
        for r in range(self.sp_model.rowCount()):
            v = self.sp_model.record(r).value("num_product")
            if v not in (None, "", 0):
                used_products.add(v)
        free_product_id = None
        for pid, _name in self._products:
            if pid not in used_products:
                free_product_id = pid
                break
        for row in range(first, last + 1):
            rec = self.sp_model.record(row)
            if rec.isNull("num_shop"):
                self.sp_model.setData(
                    self.sp_model.index(row, 1), int(shop_id), Qt.EditRole
                )
            if rec.isNull("num_product") and free_product_id is not None:
                self.sp_model.setData(
                    self.sp_model.index(row, 0),
                    int(free_product_id),
                    Qt.EditRole,
                )

    def _on_shop_changed(self, current, previous):
        if not current.isValid():
            return
        shop_id = self.shop_model.record(current.row()).value("number")
        self._base_filter = f'num_shop = {shop_id}'
        # В этой форме может не быть блока поиска в .ui.
        search_input = getattr(self, "searchInput", None)
        combo = getattr(self, "comboColumn", None)
        if search_input is not None:
            val = search_input.text().strip()
        else:
            val = ""
        if val and combo is not None:
            col = SHOP_SEARCH_COLS.get(combo.currentText(), "name")
            self.sp_model.setFilter(
                f"{self._base_filter} AND \"{col}\"::text ILIKE '%{val}%'"
            )
        else:
            self.sp_model.setFilter(self._base_filter)
        self.sp_model.select()


# ============================================================
#  6. Форма «Полная информация» (VIEW)
# ============================================================
class ShopFullInfoForm(QWidget):
    _instance = None

    @classmethod
    def instance(cls):
        if cls._instance is None or not cls._instance.isVisible():
            cls._instance = cls()
        cls._instance.show()
        cls._instance.activateWindow()
        return cls._instance

    def __init__(self):
        super().__init__()
        uic.loadUi(ui_path("shop_full_info_form.ui"), self)

        self.model = QSqlTableModel()
        self.model.setTable("shop_full_info")
        self.model.select()

        headers = {0: "№", 1: "Название", 2: "Полный адрес",
                   3: "Телефон", 4: "Открыт", 5: "Дата откр.", 6: "Филиал"}
        for c, n in headers.items():
            self.model.setHeaderData(c, Qt.Horizontal, n)

        self.tableView.setModel(self.model)
        self.tableView.horizontalHeader().setStretchLastSection(True)

        self.btnRefresh.clicked.connect(lambda: self.model.select())
