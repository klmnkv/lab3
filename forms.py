"""
forms.py — Формы приложения для работы с БД educationDB.

Реализованные концепции:
  - Master-Detail (1:M): Branch_office → Shop
  - M:M: Product ↔ Shop через Shop_Product
  - Singleton для каждой формы
  - Подстановочные поля (Lookup) через QSqlRelationalTableModel
  - Вычисляемые колонки (GENERATED + VIEW)
  - Поиск и фильтрация
  - Навигация по записям (аналог BindingNavigator)
  - Обработка ошибок при CRUD-операциях
  - Диалог выбора филиала
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableView, QLabel,
    QLineEdit, QComboBox, QPushButton, QToolBar, QAction,
    QMessageBox, QDialog, QHeaderView, QSplitter, QFormLayout,
    QDateEdit, QGroupBox, QCheckBox, QStatusBar, QAbstractItemView
)
from PyQt5.QtSql import (
    QSqlTableModel, QSqlRelationalTableModel, QSqlRelation,
    QSqlRelationalDelegate, QSqlQuery
)
from PyQt5.QtCore import Qt, QDate, QSortFilterProxyModel

# Импорт переиспользуемых виджетов
from widget import NavigationToolbar, SearchPanel, ReadOnlyDelegate, StatusLabel


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
        self.setWindowTitle("Филиалы (Branch_office)")
        self.resize(900, 500)

        self.model = QSqlTableModel()
        self.model.setTable('"Branch_office"')
        self.model.setEditStrategy(QSqlTableModel.OnManualSubmit)
        self.model.select()

        # Заголовки колонок
        headers = {
            0: "№", 1: "Название", 2: "Регион", 3: "Населённый пункт",
            4: "Адрес", 5: "Дата открытия", 6: "Телефон",
            7: "Директор", 8: "Фото"
        }
        for col, name in headers.items():
            self.model.setHeaderData(col, Qt.Horizontal, name)

        layout = QVBoxLayout(self)

        # Поиск
        search_cols = [
            ("Название", "name"), ("Регион", "region"),
            ("Населённый пункт", "locality"), ("Адрес", "address"),
            ("Директор", "director's name")
        ]
        self.search = SearchPanel(self.model, search_cols)
        layout.addWidget(self.search)

        # Таблица
        self.view = QTableView()
        self.view.setModel(self.model)
        self.view.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.view.setAlternatingRowColors(True)
        self.view.horizontalHeader().setStretchLastSection(True)
        self.view.setColumnHidden(8, True)  # Скрыть фото (bytea)
        layout.addWidget(self.view)

        # Навигация
        self.navbar = NavigationToolbar(self.view, self.model, self)
        layout.insertWidget(0, self.navbar)


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
        self.setWindowTitle("Продукты (Product)")
        self.resize(500, 400)

        self.model = QSqlTableModel()
        self.model.setTable('"Product"')
        self.model.setEditStrategy(QSqlTableModel.OnManualSubmit)
        self.model.select()

        self.model.setHeaderData(0, Qt.Horizontal, "№")
        self.model.setHeaderData(1, Qt.Horizontal, "Название")
        self.model.setHeaderData(2, Qt.Horizontal, "Ед. изм.")

        layout = QVBoxLayout(self)

        # Поиск
        search_cols = [("Название", "name"), ("Ед. изм.", "units")]
        self.search = SearchPanel(self.model, search_cols)
        layout.addWidget(self.search)

        self.view = QTableView()
        self.view.setModel(self.model)
        self.view.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.view.setAlternatingRowColors(True)
        self.view.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.view)

        self.navbar = NavigationToolbar(self.view, self.model, self)
        layout.insertWidget(0, self.navbar)


# ============================================================
#  3. Диалог выбора филиала (BranchSelectDialog)
# ============================================================
class BranchSelectDialog(QDialog):
    """Вызывается из формы Магазины для выбора филиала."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Выбрать филиал")
        self.resize(600, 400)
        self.selected_id = None

        self.model = QSqlTableModel()
        self.model.setTable('"Branch_office"')
        self.model.select()

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Выберите филиал и нажмите «Выбрать»:"))

        self.view = QTableView()
        self.view.setModel(self.model)
        self.view.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.view.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.view.setAlternatingRowColors(True)
        self.view.setColumnHidden(8, True)
        self.view.horizontalHeader().setStretchLastSection(True)
        self.view.doubleClicked.connect(self._accept)
        layout.addWidget(self.view)

        btn_layout = QHBoxLayout()
        btn_select = QPushButton("✅ Выбрать")
        btn_select.clicked.connect(self._accept)
        btn_cancel = QPushButton("Отмена")
        btn_cancel.clicked.connect(self.reject)
        btn_layout.addStretch()
        btn_layout.addWidget(btn_select)
        btn_layout.addWidget(btn_cancel)
        layout.addLayout(btn_layout)

    def _accept(self):
        row = self.view.currentIndex().row()
        if row >= 0:
            self.selected_id = self.model.record(row).value("number")
            self.selected_name = self.model.record(row).value("name")
            self.accept()
        else:
            QMessageBox.warning(self, "Внимание", "Выберите филиал!")


# ============================================================
#  4. Форма «Магазины» — Master-Detail (Branch_office → Shop)
#     + кнопка выбора филиала + подстановочные поля
# ============================================================
class ShopForm(QWidget):
    """
    Верхняя часть: список филиалов (master).
    Нижняя часть: магазины выбранного филиала (detail).
    Lookup: number_office → название филиала.
    """
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
        self.setWindowTitle("Магазины (Master-Detail: Филиал → Магазины)")
        self.resize(1000, 650)

        layout = QVBoxLayout(self)

        splitter = QSplitter(Qt.Vertical)

        # ---- MASTER: Branch_office ----
        master_group = QGroupBox("Филиалы (Branch_office)")
        master_layout = QVBoxLayout(master_group)

        self.master_model = QSqlTableModel()
        self.master_model.setTable('"Branch_office"')
        self.master_model.setEditStrategy(QSqlTableModel.OnManualSubmit)
        self.master_model.select()

        headers_m = {0: "№", 1: "Название", 2: "Регион", 3: "Нас.пункт",
                     4: "Адрес", 5: "Дата откр.", 6: "Телефон", 7: "Директор"}
        for c, n in headers_m.items():
            self.master_model.setHeaderData(c, Qt.Horizontal, n)

        self.master_view = QTableView()
        self.master_view.setModel(self.master_model)
        self.master_view.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.master_view.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.master_view.setAlternatingRowColors(True)
        self.master_view.setColumnHidden(8, True)
        self.master_view.horizontalHeader().setStretchLastSection(True)
        self.master_view.selectionModel().currentRowChanged.connect(
            self._on_master_changed
        )
        master_layout.addWidget(self.master_view)
        splitter.addWidget(master_group)

        # ---- DETAIL: Shop ----
        detail_group = QGroupBox("Магазины выбранного филиала (Shop)")
        detail_layout = QVBoxLayout(detail_group)

        # Подстановочная модель: number_office → Branch_office.name
        self.detail_model = QSqlRelationalTableModel()
        self.detail_model.setTable('"Shop"')
        self.detail_model.setEditStrategy(QSqlTableModel.OnManualSubmit)
        # Колонка 8 (number_office) → подставить name из Branch_office
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

        # Поиск по магазинам
        search_cols = [("Название", "name"), ("Нас.пункт", "locality"),
                       ("Улица", "street")]
        self.search = SearchPanel(self.detail_model, search_cols)
        detail_layout.addWidget(self.search)

        self.detail_view = QTableView()
        self.detail_view.setModel(self.detail_model)
        self.detail_view.setItemDelegate(
            QSqlRelationalDelegate(self.detail_view)
        )
        self.detail_view.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.detail_view.setAlternatingRowColors(True)
        self.detail_view.horizontalHeader().setStretchLastSection(True)
        detail_layout.addWidget(self.detail_view)

        # Навигация + кнопка выбора филиала
        self.navbar = NavigationToolbar(
            self.detail_view, self.detail_model, self
        )

        sep = self.navbar.addSeparator()
        btn_select = QAction("📋 Выбрать филиал...", self)
        btn_select.setToolTip("Открыть справочник филиалов для выбора")
        btn_select.triggered.connect(self._select_branch)
        self.navbar.addAction(btn_select)

        detail_layout.insertWidget(0, self.navbar)
        splitter.addWidget(detail_group)

        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)
        layout.addWidget(splitter)

        # Выбрать первый филиал
        if self.master_model.rowCount() > 0:
            self.master_view.selectRow(0)

    def _autofill_office_on_insert(self, parent, first, last):
        """При добавлении новой строки в detail-таблицу Shop
        автоматически подставить number_office из выбранного
        в master-таблице филиала.

        Колонка 8 — relation в QSqlRelationalTableModel.
        setData на relation-колонке принимает DISPLAY-значение
        (имя филиала), по нему Qt находит FK в dictionary;
        сырой id числом → setData возвращает false → FK не
        пишется → INSERT уходит с NULL."""
        current = self.master_view.currentIndex()
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
            # Для relation-колонки сначала пишем DISPLAY-значение.
            # На некоторых сборках Qt это может вернуть False, если
            # relation model ещё не успела подгрузиться — тогда
            # страхуемся прямой записью FK через setRecord.
            ok = self.detail_model.setData(
                self.detail_model.index(row, 8),
                office_name, Qt.EditRole
            )
            if not ok:
                rec.setValue("number_office", office_id)
                self.detail_model.setRecord(row, rec)
            if rec.isNull("open"):
                self.detail_model.setData(
                    self.detail_model.index(row, 6), 1, Qt.EditRole
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
        current = self.master_view.currentIndex()
        if not current.isValid():
            return
        office_id = self.master_model.record(current.row()).value("number")
        if office_id in (None, "", 0):
            return
        idx_fk = record.indexOf("number_office")
        if idx_fk >= 0:
            record.setValue(idx_fk, office_id)
        idx_open = record.indexOf("open")
        if idx_open >= 0 and record.isNull(idx_open):
            record.setValue(idx_open, 1)

    def _on_master_changed(self, current, previous):
        """При выборе филиала — фильтровать магазины."""
        if not current.isValid():
            return
        office_id = self.master_model.record(current.row()).value("number")
        self.detail_model.setFilter(f'number_office = {office_id}')
        self.detail_model.select()

    def _select_branch(self):
        """Открыть диалог выбора филиала — записать FK в текущую строку."""
        dlg = BranchSelectDialog(self)
        if dlg.exec_() != QDialog.Accepted or dlg.selected_id is None:
            return

        row = self.detail_view.currentIndex().row()
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
        if self.master_view.currentIndex().isValid():
            self._on_master_changed(self.master_view.currentIndex(), None)


# ============================================================
#  5. Форма «Товары в магазинах» (Shop_Product) — M:M
#     + вычисляемые колонки + подстановочные поля
# ============================================================
class ShopProductForm(QWidget):
    """
    Верхняя часть: список магазинов (Shop).
    Нижняя часть: товары выбранного магазина (Shop_Product).
    Lookup: num_product → Product.name.
    Вычисляемое поле: revenue_for_the_prod (GENERATED в БД).
    """
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
        self.setWindowTitle(
            "Товары в магазинах (M:M: Product ↔ Shop через Shop_Product)"
        )
        self.resize(1000, 650)

        layout = QVBoxLayout(self)
        splitter = QSplitter(Qt.Vertical)

        # ---- MASTER: Shop ----
        shop_group = QGroupBox("Магазины (Shop)")
        shop_layout = QVBoxLayout(shop_group)

        self.shop_model = QSqlTableModel()
        self.shop_model.setTable('"Shop"')
        self.shop_model.select()

        shop_headers = {0: "№", 1: "Название", 2: "Нас.пункт", 3: "Улица",
                        4: "Дом", 5: "Телефон", 6: "Открыт", 7: "Дата откр.",
                        8: "Филиал (id)"}
        for c, n in shop_headers.items():
            self.shop_model.setHeaderData(c, Qt.Horizontal, n)

        self.shop_view = QTableView()
        self.shop_view.setModel(self.shop_model)
        self.shop_view.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.shop_view.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.shop_view.setAlternatingRowColors(True)
        self.shop_view.horizontalHeader().setStretchLastSection(True)
        self.shop_view.selectionModel().currentRowChanged.connect(
            self._on_shop_changed
        )
        shop_layout.addWidget(self.shop_view)
        splitter.addWidget(shop_group)

        # ---- DETAIL: Shop_Product ----
        sp_group = QGroupBox("Товары в выбранном магазине (Shop_Product)")
        sp_layout = QVBoxLayout(sp_group)

        self.sp_model = QSqlRelationalTableModel()
        self.sp_model.setTable('"Shop_Product"')
        self.sp_model.setEditStrategy(QSqlTableModel.OnManualSubmit)
        # Lookup: num_product (кол. 0) → Product.name
        self.sp_model.setRelation(
            0, QSqlRelation('"Product"', 'number', 'name')
        )
        self.sp_model.select()

        # Автоподстановка num_shop при добавлении новой строки в Shop_Product
        self.sp_model.rowsInserted.connect(self._autofill_shop_on_insert)

        sp_headers = {0: "Продукт", 1: "Магазин (id)", 2: "Кол-во",
                      3: "Цена за ед.", 4: "Выручка (авто)"}
        for c, n in sp_headers.items():
            self.sp_model.setHeaderData(c, Qt.Horizontal, n)

        self.sp_view = QTableView()
        self.sp_view.setModel(self.sp_model)
        self.sp_view.setItemDelegate(QSqlRelationalDelegate(self.sp_view))
        self.sp_view.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.sp_view.setAlternatingRowColors(True)
        self.sp_view.horizontalHeader().setStretchLastSection(True)
        sp_layout.addWidget(self.sp_view)

        self.navbar = NavigationToolbar(self.sp_view, self.sp_model, self)
        sp_layout.insertWidget(0, self.navbar)

        splitter.addWidget(sp_group)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)
        layout.addWidget(splitter)

        # Информационная панель снизу
        info = QLabel(
            "ℹ️  Колонка «Выручка» = quantity × price_per_unit "
            "(GENERATED ALWAYS AS в PostgreSQL). Пересчитывается "
            "автоматически после сохранения."
        )
        info.setStyleSheet("color: #555; font-style: italic; padding: 4px;")
        info.setWordWrap(True)
        layout.addWidget(info)

        if self.shop_model.rowCount() > 0:
            self.shop_view.selectRow(0)

    def _on_shop_changed(self, current, previous):
        """При выборе магазина — фильтровать товары."""
        if not current.isValid():
            return
        shop_id = self.shop_model.record(current.row()).value("number")
        self.sp_model.setFilter(f'num_shop = {shop_id}')
        self.sp_model.select()

    def _autofill_shop_on_insert(self, parent, first, last):
        """При добавлении новой строки в Shop_Product автоматически
        подставить num_shop из выбранного магазина (master).
        num_shop — обычный INTEGER FK (не relation), setData
        принимает сырое число."""
        current = self.shop_view.currentIndex()
        if not current.isValid():
            return
        shop_id = self.shop_model.record(current.row()).value("number")
        if shop_id in (None, "", 0):
            return
        for row in range(first, last + 1):
            rec = self.sp_model.record(row)
            if rec.isNull("num_shop"):
                self.sp_model.setData(
                    self.sp_model.index(row, 1), shop_id, Qt.EditRole
                )


# ============================================================
#  6. Форма «Полная информация» (VIEW shop_full_info)
# ============================================================
class ShopFullInfoForm(QWidget):
    """Просмотр представления (VIEW) с вычисляемыми колонками."""
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
        self.setWindowTitle("Полная информация о магазинах (VIEW shop_full_info)")
        self.resize(800, 450)

        self.model = QSqlTableModel()
        self.model.setTable("shop_full_info")
        self.model.select()

        headers = {0: "№", 1: "Название", 2: "Полный адрес",
                   3: "Телефон", 4: "Открыт", 5: "Дата откр.",
                   6: "Филиал"}
        for c, n in headers.items():
            self.model.setHeaderData(c, Qt.Horizontal, n)

        layout = QVBoxLayout(self)

        info = QLabel(
            "📊 Данные из VIEW shop_full_info. "
            "Колонки full_address и branch_name — вычисляемые. "
            "Только чтение."
        )
        info.setStyleSheet("color: #2E4057; font-weight: bold; padding: 6px;")
        info.setWordWrap(True)
        layout.addWidget(info)

        self.view = QTableView()
        self.view.setModel(self.model)
        self.view.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.view.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.view.setAlternatingRowColors(True)
        self.view.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.view)

        btn_refresh = QPushButton("🔄 Обновить")
        btn_refresh.clicked.connect(lambda: self.model.select())
        layout.addWidget(btn_refresh)
