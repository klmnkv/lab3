"""
forms_lab2.py — Формы для Лабораторной работы №2.

ЛР №2 посвящена работе с РОДИТЕЛЬСКИМИ таблицами (без внешних ключей).
В нашей БД educationDB это:
    - Branch_office (Филиалы)  — аналог "Сотрудники" из методички
    - Product       (Продукты) — аналог "Блюда"      из методички

Реализованные особенности (по заданию ЛР №2):
    - Несколько форм в проекте.
    - Различные элементы управления:
        Label, QLineEdit (TextBox), QComboBox, QListWidget (ListBox),
        QCheckBox, QLabel-PictureBox, QTableView (DataGridView),
        NavigationToolbar (BindingNavigator).
    - Представление "Details": каждое поле — отдельный компонент,
      синхронизирован с DataGridView внизу формы (mapper).
    - Работа с графическим полем: загрузка фото из файла и очистка.
    - ComboBox/ListBox для полей с CHECK-ограничением (Product.name,
      Product.units).
    - Поиск + фильтрация (как в методичке: TextBox + CheckBox Фильтр).
    - Шаблон проектирования "Одиночка" (Singleton) для всех форм.
    - Обработка исключений при сохранении (повторяющийся регион,
      неверный формат телефона и т. п.).
"""

import os
from PyQt5 import uic
from PyQt5.QtWidgets import (
    QWidget, QMessageBox, QFileDialog, QDataWidgetMapper,
    QAbstractItemView, QHeaderView, QStyledItemDelegate, QTableView,
    QComboBox
)
from PyQt5.QtSql import QSqlTableModel
from PyQt5.QtCore import Qt, QByteArray, QDate, QModelIndex
from PyQt5.QtGui import QPixmap, QImage

from widget import NavigationToolbar


# Папка с .ui-файлами рядом с этим модулем
UI_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ui")


def ui_path(filename: str) -> str:
    return os.path.join(UI_DIR, filename)


# ============================================================
#  Делегат, который пробрасывает данные между моделью и
#  ComboBox / QListWidget по их текущему тексту/выделению.
#  QDataWidgetMapper по умолчанию работает только со
#  стандартным userProperty (для QComboBox это currentText —
#  уже хорошо; для QListWidget — нет, нужен делегат).
# ============================================================
class ComboTextDelegate(QStyledItemDelegate):
    """Связывает QComboBox с моделью по тексту (а не по индексу).
    Для прочих виджетов (QLineEdit, QDateEdit и т.п.) — поведение
    по умолчанию, чтобы можно было ставить делегат на mapper целиком."""

    def setEditorData(self, editor, index):
        if not isinstance(editor, QComboBox):
            super().setEditorData(editor, index)
            return
        value = index.model().data(index, Qt.EditRole)
        if value is None:
            return
        i = editor.findText(str(value))
        if i >= 0:
            editor.setCurrentIndex(i)
        else:
            editor.setEditText(str(value))

    def setModelData(self, editor, model, index):
        if not isinstance(editor, QComboBox):
            super().setModelData(editor, model, index)
            return
        model.setData(index, editor.currentText(), Qt.EditRole)


# ============================================================
#  1. Форма «Филиалы (Details)» — Branch_office
# ============================================================
class BranchOfficeDetailsForm(QWidget):
    """Details-форма для родительской таблицы Branch_office.

    Структура (сверху вниз):
        Поиск/фильтр → Details (поля + фото) → DataGridView → подсказка.
    Навигатор записей (BindingNavigator-аналог) добавляется в код наверху.
    """

    _instance = None  # Singleton

    # Имена колонок в БД (для фильтра по выбранной в ComboBox колонке)
    SEARCH_COLS = {
        "Название": "name",
        "Регион": "region",
        "Населённый пункт": "locality",
        "Адрес": "address",
        "Директор": "director's name",
    }

    @classmethod
    def instance(cls):
        if cls._instance is None or not cls._instance.isVisible():
            cls._instance = cls()
        cls._instance.show()
        cls._instance.activateWindow()
        return cls._instance

    def __init__(self):
        super().__init__()
        uic.loadUi(ui_path("branch_office_details_form.ui"), self)

        # ---------- Модель ----------
        self.model = QSqlTableModel()
        self.model.setTable('"Branch_office"')
        self.model.setEditStrategy(QSqlTableModel.OnManualSubmit)
        self.model.select()

        headers = {
            0: "№", 1: "Название", 2: "Регион", 3: "Нас. пункт",
            4: "Адрес", 5: "Дата откр.", 6: "Телефон",
            7: "Директор", 8: "Фото",
        }
        for col, name in headers.items():
            self.model.setHeaderData(col, Qt.Horizontal, name)

        # Скрытый QTableView — нужен NavigationToolbar'у для управления
        # текущей строкой и синхронизации с QDataWidgetMapper.
        # В карточке (Details) список филиалов не показывается.
        self.tableView = QTableView(self)
        self.tableView.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tableView.setSelectionMode(QAbstractItemView.SingleSelection)
        self.tableView.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tableView.setModel(self.model)
        self.tableView.hide()

        # ---------- Навигатор (аналог BindingNavigator) ----------
        self.navbar = NavigationToolbar(self.tableView, self.model, self)
        self.layout().insertWidget(0, self.navbar)
        # При сохранении / ошибке — обновим карточку
        self.navbar.record_saved.connect(self._refresh_after_save)

        # ---------- Mapper: Details ↔ модель ----------
        # Связывает виджеты в карточке со столбцами текущей строки.
        self.mapper = QDataWidgetMapper(self)
        self.mapper.setModel(self.model)
        self.mapper.setSubmitPolicy(QDataWidgetMapper.AutoSubmit)

        self.mapper.addMapping(self.editNumber,    0)  # number      (read-only)
        # Скрыть PK у родительской таблицы Branch_office
        self.editNumber.hide()
        self.lblNumber.hide()
        self.mapper.addMapping(self.editName,      1)  # name
        self.mapper.addMapping(self.editRegion,    2)  # region
        self.mapper.addMapping(self.editLocality,  3)  # locality
        self.mapper.addMapping(self.editAddress,   4)  # address
        self.mapper.addMapping(self.dateOpening,   5)  # opening_date
        self.mapper.addMapping(self.editPhone,     6)  # phone
        self.mapper.addMapping(self.editDirector,  7)  # director's name
        # Колонка 8 (фото) обрабатывается вручную — см. _on_row_changed()

        # При смене строки в таблице — обновить карточку
        self.tableView.selectionModel().currentRowChanged.connect(
            self._on_row_changed
        )

        # При перемещении мэппера — обновить фото (его не привязать
        # стандартно: BYTEA → QPixmap нужно конвертировать)
        self.mapper.currentIndexChanged.connect(self._refresh_photo)

        # Установить первую строку как текущую
        if self.model.rowCount() > 0:
            self.tableView.selectRow(0)
            self.mapper.toFirst()

        # ---------- Поиск/фильтр ----------
        self.btnFind.clicked.connect(self._apply_search)
        self.searchInput.returnPressed.connect(self._apply_search)
        self.btnReset.clicked.connect(self._reset_search)
        self.checkBoxFilter.stateChanged.connect(self._apply_search)

        # ---------- Работа с фото ----------
        self.btnOpenPhoto.clicked.connect(self._open_photo)
        self.btnClearPhoto.clicked.connect(self._clear_photo)

        # Хранилище для текущего фото (bytes), чтобы сохранять корректно
        self._current_photo_bytes: bytes | None = None

    # ------------------------------------------------------------
    #  Синхронизация Details с выделенной строкой DataGridView
    # ------------------------------------------------------------
    def _on_row_changed(self, current: QModelIndex, _previous: QModelIndex):
        if current.isValid():
            self.mapper.setCurrentIndex(current.row())

    def _refresh_after_save(self):
        """После сохранения позиция в модели может «съехать» — повторно
        выберем строку и обновим карточку."""
        row = self.tableView.currentIndex().row()
        if row < 0 and self.model.rowCount() > 0:
            row = 0
            self.tableView.selectRow(0)
        if row >= 0:
            self.mapper.setCurrentIndex(row)

    # ------------------------------------------------------------
    #  Работа с графическим полем (PictureBox-аналог)
    # ------------------------------------------------------------
    def _refresh_photo(self, row: int):
        """Прочитать BYTEA из текущей строки и показать в QLabel."""
        if row < 0 or row >= self.model.rowCount():
            self._set_photo_pixmap(None)
            return
        record = self.model.record(row)
        raw = record.value('director\'s photo')

        # raw может прийти как None / QByteArray / bytes
        data: bytes | None = None
        if isinstance(raw, QByteArray) and not raw.isNull() and raw.size() > 0:
            data = bytes(raw)
        elif isinstance(raw, (bytes, bytearray)) and len(raw) > 0:
            data = bytes(raw)

        self._current_photo_bytes = data
        if data is None:
            self._set_photo_pixmap(None)
            self.checkBoxHasPhoto.setChecked(False)
            return

        pix = QPixmap()
        if pix.loadFromData(data):
            self._set_photo_pixmap(pix)
            self.checkBoxHasPhoto.setChecked(True)
        else:
            self._set_photo_pixmap(None)
            self.checkBoxHasPhoto.setChecked(False)

    def _set_photo_pixmap(self, pix: QPixmap | None):
        if pix is None or pix.isNull():
            self.photoBox.setPixmap(QPixmap())  # очистить
            self.photoBox.setText("(нет фото)")
            return
        scaled = pix.scaled(
            self.photoBox.size(),
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation,
        )
        self.photoBox.setPixmap(scaled)
        self.photoBox.setText("")

    def _open_photo(self):
        """Загрузить фото из файла (BMP/JPG/PNG/GIF/TIFF)."""
        row = self.tableView.currentIndex().row()
        if row < 0:
            QMessageBox.warning(
                self, "Внимание",
                "Сначала выберите запись в списке.",
            )
            return

        path, _ = QFileDialog.getOpenFileName(
            self,
            "Укажите файл для фото",
            "",
            "Изображения (*.png *.jpg *.jpeg *.bmp *.gif *.tif *.tiff);;"
            "Все файлы (*.*)",
        )
        if not path:
            return

        # Проверим, что Qt действительно может прочитать формат
        try:
            img = QImage(path)
            if img.isNull():
                raise ValueError("Не удалось декодировать изображение")
        except Exception as exc:
            QMessageBox.critical(
                self, "Ошибка",
                f"Выбран не тот формат файла.\n\nПодробности: {exc}",
            )
            return

        with open(path, "rb") as f:
            data = f.read()

        # Обновить поле в модели (BYTEA-колонка №8)
        ok = self.model.setData(
            self.model.index(row, 8),
            QByteArray(data),
            Qt.EditRole,
        )
        if not ok:
            QMessageBox.warning(
                self, "Внимание",
                "Не удалось присвоить фото текущей записи.",
            )
            return

        # Обновим UI и попросим пользователя нажать «Сохранить»
        self._current_photo_bytes = data
        pix = QPixmap()
        pix.loadFromData(data)
        self._set_photo_pixmap(pix)
        self.checkBoxHasPhoto.setChecked(True)

        QMessageBox.information(
            self, "Фото загружено",
            "Фото добавлено в текущую запись.\n"
            "Не забудьте нажать кнопку 💾 на навигаторе для сохранения в БД.",
        )

    def _clear_photo(self):
        row = self.tableView.currentIndex().row()
        if row < 0:
            return
        self.model.setData(self.model.index(row, 8), None, Qt.EditRole)
        self._current_photo_bytes = None
        self._set_photo_pixmap(None)
        self.checkBoxHasPhoto.setChecked(False)

    # ------------------------------------------------------------
    #  Поиск и фильтрация
    # ------------------------------------------------------------
    def _apply_search(self):
        val = self.searchInput.text().strip()
        col_label = self.comboColumn.currentText()
        col = self.SEARCH_COLS.get(col_label, "name")

        if not val:
            self._reset_search()
            return

        # Экранируем одиночные кавычки в значении
        safe = val.replace("'", "''")

        if self.checkBoxFilter.isChecked():
            # Точное совпадение (как cотрудникиBindingSource.Filter)
            self.model.setFilter(f'"{col}"::text = \'{safe}\'')
        else:
            # Поиск-подстрока
            self.model.setFilter(f'"{col}"::text ILIKE \'%{safe}%\'')

        if not self.model.select():
            QMessageBox.warning(
                self, "Ошибка фильтрации",
                self.model.lastError().text(),
            )
            return

        if self.model.rowCount() == 0:
            QMessageBox.information(
                self, "Поиск", "Нет записей, удовлетворяющих условию.",
            )

    def _reset_search(self):
        self.searchInput.clear()
        self.checkBoxFilter.setChecked(False)
        self.model.setFilter("")
        self.model.select()
        if self.model.rowCount() > 0:
            self.tableView.selectRow(0)


# ============================================================
#  2. Форма «Продукты (Details)» — Product
# ============================================================
class ProductDetailsForm(QWidget):
    """Details-форма для родительской таблицы Product.

    Демонстрирует ComboBox + ListWidget для полей с CHECK-ограничением,
    что точно соответствует методичке ЛР №2 (поле «Единицы»).
    """

    _instance = None

    SEARCH_COLS = {
        "Категория": "category",
        "Название": "name",
        "Ед. изм.": "units",
    }

    @classmethod
    def instance(cls):
        if cls._instance is None or not cls._instance.isVisible():
            cls._instance = cls()
        cls._instance.show()
        cls._instance.activateWindow()
        return cls._instance

    def __init__(self):
        super().__init__()
        uic.loadUi(ui_path("product_details_form.ui"), self)

        # ---------- Модель ----------
        self.model = QSqlTableModel()
        self.model.setTable('"Product"')
        self.model.setEditStrategy(QSqlTableModel.OnManualSubmit)
        self.model.select()

        self.model.setHeaderData(0, Qt.Horizontal, "№")
        self.model.setHeaderData(1, Qt.Horizontal, "Категория")
        self.model.setHeaderData(2, Qt.Horizontal, "Ед. изм.")
        self.model.setHeaderData(3, Qt.Horizontal, "Название")

        # Скрытый QTableView — нужен NavigationToolbar'у для управления
        # текущей строкой и синхронизации с QDataWidgetMapper.
        # В карточке (Details) список продуктов не показывается.
        self.tableView = QTableView(self)
        self.tableView.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tableView.setSelectionMode(QAbstractItemView.SingleSelection)
        self.tableView.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tableView.setModel(self.model)
        self.tableView.hide()

        # ---------- Навигатор ----------
        self.navbar = NavigationToolbar(self.tableView, self.model, self)
        self.layout().insertWidget(0, self.navbar)
        self.navbar.record_saved.connect(self._refresh_after_save)

        # ---------- Mapper ----------
        self.mapper = QDataWidgetMapper(self)
        self.mapper.setModel(self.model)
        self.mapper.setSubmitPolicy(QDataWidgetMapper.AutoSubmit)

        # Делегат для ComboBox (category): связывает с моделью по тексту
        self._combo_delegate = ComboTextDelegate(self)

        self.mapper.addMapping(self.editNumber, 0)  # number — read-only
        # Скрыть PK у родительской таблицы Product
        self.editNumber.hide()
        self.lblNumber.hide()
        self.mapper.addMapping(self.comboCategory, 1)  # category (CHECK-список)
        self.mapper.addMapping(self.editName, 3)       # name (свободный текст)
        # Для units используется ListWidget. QDataWidgetMapper не
        # умеет его мапить стандартно, поэтому синхронизируем вручную:
        #   модель → список: в _on_row_changed
        #   список → модель: в _on_list_units_changed
        self.mapper.setItemDelegate(self._combo_delegate)
        self.listUnits.itemSelectionChanged.connect(self._on_list_units_changed)

        self.tableView.selectionModel().currentRowChanged.connect(
            self._on_row_changed
        )

        # Автозаполнение значений по умолчанию для NOT NULL полей
        # при добавлении новой строки (category, units). Используем
        # rowsInserted + setData (надёжнее, чем primeInsert+setValue
        # в PyQt5 — последний не всегда переносит правки обратно
        # в модель).
        self.model.rowsInserted.connect(self._autofill_product_defaults)

        # Перейти к первой записи
        if self.model.rowCount() > 0:
            self.tableView.selectRow(0)
            self.mapper.toFirst()

        # ---------- Поиск/фильтр ----------
        self.btnFind.clicked.connect(self._apply_search)
        self.searchInput.returnPressed.connect(self._apply_search)
        self.btnReset.clicked.connect(self._reset_search)
        self.checkBoxFilter.stateChanged.connect(self._apply_search)

    # ------------------------------------------------------------
    def _on_row_changed(self, current: QModelIndex, _previous: QModelIndex):
        if current.isValid():
            self.mapper.setCurrentIndex(current.row())
            # Синхронизировать ListWidget с текущим значением units
            value = self.model.record(current.row()).value("units")
            if value:
                items = self.listUnits.findItems(str(value), Qt.MatchExactly)
                self.listUnits.blockSignals(True)
                self.listUnits.clearSelection()
                if items:
                    items[0].setSelected(True)
                    self.listUnits.setCurrentItem(items[0])
                self.listUnits.blockSignals(False)

    def _on_list_units_changed(self):
        """При выборе единицы в ListWidget — записать значение в модель."""
        item = self.listUnits.currentItem()
        if item is None:
            return
        row = self.mapper.currentIndex()
        if row < 0:
            return
        self.model.setData(
            self.model.index(row, 2), item.text(), Qt.EditRole
        )

    def _autofill_product_defaults(self, parent, first, last):
        """Подставить значения по умолчанию для NOT NULL полей Product
        при добавлении новой строки. Без этого PostgreSQL отдаёт 23502
        (null value in NOT NULL column 'units').

        Также синхронизируем виджеты Details (combo/list/lineEdit),
        иначе после refresh они визуально пусты, а под ними в модели
        уже подставлены дефолты."""
        for row in range(first, last + 1):
            rec = self.model.record(row)
            if rec.isNull("category") or not rec.value("category"):
                self.model.setData(
                    self.model.index(row, 1), "другое", Qt.EditRole
                )
            if rec.isNull("units") or not rec.value("units"):
                self.model.setData(
                    self.model.index(row, 2), "шт", Qt.EditRole
                )
        # Перевести таблицу/маппер на свежедобавленную строку,
        # чтобы дефолты сразу отобразились в combo/list/lineEdit.
        self.tableView.selectRow(last)
        self.mapper.setCurrentIndex(last)

    def _refresh_after_save(self):
        row = self.tableView.currentIndex().row()
        if row < 0 and self.model.rowCount() > 0:
            row = 0
            self.tableView.selectRow(0)
        if row >= 0:
            self.mapper.setCurrentIndex(row)

    # ------------------------------------------------------------
    #  Поиск/фильтр
    # ------------------------------------------------------------
    def _apply_search(self):
        val = self.searchInput.text().strip()
        col_label = self.comboColumn.currentText()
        col = self.SEARCH_COLS.get(col_label, "name")

        if not val:
            self._reset_search()
            return

        safe = val.replace("'", "''")

        if self.checkBoxFilter.isChecked():
            self.model.setFilter(f'"{col}"::text = \'{safe}\'')
        else:
            self.model.setFilter(f'"{col}"::text ILIKE \'%{safe}%\'')

        if not self.model.select():
            QMessageBox.warning(
                self, "Ошибка фильтрации",
                self.model.lastError().text(),
            )
            return

        if self.model.rowCount() == 0:
            QMessageBox.information(
                self, "Поиск", "Нет записей, удовлетворяющих условию.",
            )

    def _reset_search(self):
        self.searchInput.clear()
        self.checkBoxFilter.setChecked(False)
        self.model.setFilter("")
        self.model.select()
        if self.model.rowCount() > 0:
            self.tableView.selectRow(0)
