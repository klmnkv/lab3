"""
widget.py — Переиспользуемые виджеты для приложения educationDB.

Содержит:
  - NavigationToolbar  — аналог BindingNavigator (Windows Forms)
  - SearchPanel        — панель поиска и фильтрации
  - ReadOnlyDelegate   — делегат для блокировки редактирования отдельных колонок
  - StatusLabel         — метка для отображения статуса подключения
"""
import re

from PyQt5.QtWidgets import (
    QWidget, QHBoxLayout, QTableView, QLabel, QLineEdit,
    QComboBox, QPushButton, QToolBar, QAction, QMessageBox,
    QStyledItemDelegate, QAbstractItemView, QDoubleSpinBox,
    QApplication, QAbstractItemDelegate
)
from PyQt5.QtSql import QSqlTableModel, QSqlQuery
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QColor


# ============================================================
#  NavigationToolbar — аналог BindingNavigator (Windows Forms)
# ============================================================
class NavigationToolbar(QToolBar):
    """Панель навигации по записям таблицы:
    Первая / Назад / Вперёд / Последняя /
    Добавить / Удалить / Сохранить / Отменить.

    Сигналы:
        record_saved  — после успешного сохранения
        record_error  — при ошибке (передаёт текст ошибки)
    """

    record_saved = pyqtSignal()
    record_error = pyqtSignal(str)
    row_inserted = pyqtSignal(int)  # номер свежедобавленной строки —
                                    # форма может подставить дефолты (FK и т.п.)

    def __init__(self, view: QTableView, model: QSqlTableModel, parent=None):
        super().__init__("Навигация", parent)
        self._view = view
        self._model = model
        self._server_generated_cols = None  # ленивый кэш IDENTITY/GENERATED колонок
        self._column_defaults = None         # ленивый кэш DEFAULT для NOT NULL колонок
        self._lbl = QLabel(" Запись: 0 / 0 ")
        self._lbl.setStyleSheet(
            "font-weight: bold; padding: 0 8px; color: #2E4057;"
        )
        self._build()

    def _build(self):
        # --- Навигация ---
        nav_actions = [
            ("⏮", "Первая запись (Home)",     self._first),
            ("◀",  "Предыдущая запись (PgUp)", self._prev),
        ]
        for icon, tip, slot in nav_actions:
            a = QAction(icon, self)
            a.setToolTip(tip)
            a.triggered.connect(slot)
            self.addAction(a)

        self.addWidget(self._lbl)

        nav_actions2 = [
            ("▶",  "Следующая запись (PgDn)", self._next),
            ("⏭", "Последняя запись (End)",   self._last),
        ]
        for icon, tip, slot in nav_actions2:
            a = QAction(icon, self)
            a.setToolTip(tip)
            a.triggered.connect(slot)
            self.addAction(a)

        self.addSeparator()

        # --- CRUD ---
        crud_actions = [
            ("➕", "Добавить запись (Ins)",          self._add),
            ("❌", "Удалить запись (Del)",            self._delete),
        ]
        for icon, tip, slot in crud_actions:
            a = QAction(icon, self)
            a.setToolTip(tip)
            a.triggered.connect(slot)
            self.addAction(a)

        self.addSeparator()

        save_actions = [
            ("💾", "Сохранить изменения (Ctrl+S)",   self._save),
            ("↩️",  "Отменить изменения (Ctrl+Z)",    self._revert),
        ]
        for icon, tip, slot in save_actions:
            a = QAction(icon, self)
            a.setToolTip(tip)
            a.triggered.connect(slot)
            self.addAction(a)

        # Обновление метки при смене строки
        if self._view.selectionModel():
            self._view.selectionModel().currentRowChanged.connect(
                self._update_label
            )
        self._model.modelReset.connect(self._update_label)
        self._model.dataChanged.connect(self._update_label)
        self._update_label()

        # Запретить редактирование серверно-генерируемых колонок
        # (IDENTITY и GENERATED ALWAYS AS ... STORED).
        self._apply_readonly_delegates()

    # --- Навигация ---
    def _first(self):
        if self._model.rowCount() > 0:
            self._view.selectRow(0)

    def _prev(self):
        row = self._view.currentIndex().row()
        if row > 0:
            self._view.selectRow(row - 1)

    def _next(self):
        row = self._view.currentIndex().row()
        if row < self._model.rowCount() - 1:
            self._view.selectRow(row + 1)

    def _last(self):
        n = self._model.rowCount()
        if n > 0:
            self._view.selectRow(n - 1)

    def _apply_readonly_delegates(self):
        """Навесить ReadOnlyDelegate на PK/GENERATED колонки, чтобы
        пользователь не мог их отредактировать вручную — значения
        выставляет сама БД."""
        auto_cols = self._get_server_generated_cols()
        if not auto_cols:
            return
        rec = self._model.record()
        for name in auto_cols:
            col = rec.indexOf(name)
            if col >= 0:
                self._view.setItemDelegateForColumn(
                    col, ReadOnlyDelegate(self._view)
                )

    # --- CRUD ---
    def _get_server_generated_cols(self) -> set:
        """Возвращает имена колонок, которые БД вычисляет сама
        (IDENTITY и GENERATED ALWAYS AS ... STORED). Такие колонки
        должны исключаться из INSERT, иначе PostgreSQL вернёт ошибку
        «cannot insert a non-DEFAULT value» / «cannot insert into
        generated column»."""
        if self._server_generated_cols is not None:
            return self._server_generated_cols

        table = self._model.tableName().strip('"')
        cols = set()
        q = QSqlQuery()
        q.prepare(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name = :t "
            "  AND (is_identity = 'YES' OR is_generated = 'ALWAYS')"
        )
        q.bindValue(":t", table)
        if q.exec_():
            while q.next():
                cols.add(q.value(0))
        self._server_generated_cols = cols
        return cols

    def _get_column_defaults(self) -> dict:
        """Возвращает {column_name: default_value} для NOT NULL колонок
        с DEFAULT, вычислив выражение на стороне PG (например,
        '0.00'::money → '$0.00'). Нужно, чтобы свежедобавленная строка
        не падала с not-null constraint на полях, которые пользователь
        не тронул: Qt шлёт в INSERT все поля, и NULL не заменяется
        на DEFAULT автоматически."""
        if self._column_defaults is not None:
            return self._column_defaults

        table = self._model.tableName().strip('"')
        result = {}
        q = QSqlQuery()
        q.prepare(
            "SELECT column_name, column_default "
            "FROM information_schema.columns "
            "WHERE table_name = :t "
            "  AND is_nullable = 'NO' "
            "  AND column_default IS NOT NULL "
            "  AND (is_identity IS NULL OR is_identity = 'NO') "
            "  AND (is_generated IS NULL OR is_generated = 'NEVER')"
        )
        q.bindValue(":t", table)
        if not q.exec_():
            self._column_defaults = result
            return result

        exprs = []
        while q.next():
            exprs.append((q.value(0), q.value(1)))

        for name, expr in exprs:
            ev = QSqlQuery()
            if ev.exec_(f"SELECT {expr}") and ev.next():
                val = ev.value(0)
                if val is not None:
                    result[name] = val
        self._column_defaults = result
        return result

    def _add(self):
        row = self._model.rowCount()

        # Строим пустую запись и помечаем серверно-генерируемые колонки
        # как «not generated», чтобы они не попадали в INSERT.
        rec = self._model.record()
        auto_cols = self._get_server_generated_cols()
        defaults = self._get_column_defaults()
        for i in range(rec.count()):
            field = rec.field(i)
            name = field.name()
            if name in auto_cols or field.isAutoValue():
                rec.setGenerated(i, False)
            elif name in defaults:
                # Предзаполнить DEFAULT-значение, чтобы пользователь его видел
                # и чтобы INSERT не падал на NOT NULL, если поле не тронуто.
                rec.setValue(i, defaults[name])

        # Если на модели стоит простой фильтр вида "col = value",
        # подставляем это значение в новую запись. Это критично для
        # master-detail сценариев (например, Shop.number_office),
        # где FK обязателен и должен наследоваться от фильтра detail.
        implied = self._extract_simple_filter_value()
        if implied:
            col_name, val = implied
            idx = rec.indexOf(col_name)
            if idx >= 0 and rec.isNull(idx):
                rec.setValue(idx, val)

        if not self._model.insertRecord(row, rec):
            error = self._model.lastError().text()
            QMessageBox.critical(self, "Ошибка добавления", error)
            self.record_error.emit(error)
            return

        self._view.selectRow(row)
        # Даём форме шанс подставить значения по умолчанию
        # (например, FK в master-detail) до начала редактирования.
        self.row_inserted.emit(row)
        # Начать редактирование первого редактируемого столбца
        self._view.edit(self._model.index(row, 1))

    def _delete(self):
        row = self._view.currentIndex().row()
        if row < 0:
            QMessageBox.warning(self, "Удаление", "Выберите запись для удаления.")
            return
        reply = QMessageBox.question(
            self, "Подтверждение удаления",
            f"Удалить запись (строка {row + 1})?",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self._model.removeRow(row)
            if not self._model.submitAll():
                error_text = self._model.lastError().text()
                QMessageBox.critical(self, "Ошибка удаления", error_text)
                self._model.revertAll()
                self.record_error.emit(error_text)
            else:
                self._model.select()
                self.record_saved.emit()

    def _save(self):
        # Зафиксировать активный редактор в таблице (если пользователь
        # нажал «Сохранить», не выходя из ячейки).
        editor = QApplication.focusWidget()
        if editor is not None and self._view.isAncestorOf(editor):
            # Фокус может быть на дочернем QLineEdit внутри редактора
            # (например, внутри QDoubleSpinBox). Поднимаемся до виджета,
            # который является прямым ребёнком viewport таблицы.
            commit_widget = editor
            while (
                commit_widget.parentWidget() is not None
                and commit_widget.parentWidget() != self._view.viewport()
            ):
                commit_widget = commit_widget.parentWidget()
            self._view.commitData(commit_widget)
            self._view.closeEditor(
                commit_widget, QAbstractItemDelegate.NoHint
            )

        # Последняя линия обороны: если detail-модель отфильтрована
        # как "fk = N", дозаполнить NULL в этой колонке перед submitAll().
        implied = self._extract_simple_filter_value()
        if implied:
            col_name, val = implied
            col = self._model.record().indexOf(col_name)
            if col >= 0:
                for row in range(self._model.rowCount()):
                    if self._model.record(row).isNull(col_name):
                        self._model.setData(
                            self._model.index(row, col), val, Qt.EditRole
                        )

        if not self._model.submitAll():
            error_text = self._model.lastError().text()
            QMessageBox.critical(self, "Ошибка сохранения", error_text)
            self._model.revertAll()
            self.record_error.emit(error_text)
        else:
            # Перечитать данные из БД, чтобы подтянуть авто-сгенерированные
            # PK/GENERATED колонки и синхронизировать кэш модели.
            current_row = self._view.currentIndex().row()
            self._model.select()
            if 0 <= current_row < self._model.rowCount():
                self._view.selectRow(current_row)
            self.record_saved.emit()

    def _extract_simple_filter_value(self):
        """Вернуть (column_name, int_value) для фильтра вида `col = 123`."""
        filter_expr = (self._model.filter() or "").strip()
        m = re.fullmatch(r'("?[\w]+"\.?[\w]*|[\w]+)\s*=\s*(\d+)', filter_expr)
        if not m:
            return None
        col_ref, raw_val = m.groups()
        col_name = col_ref.split(".")[-1].replace('"', "")
        return col_name, int(raw_val)

    def _revert(self):
        self._model.revertAll()

    def _update_label(self, *args):
        row = self._view.currentIndex().row() + 1
        total = self._model.rowCount()
        self._lbl.setText(f" Запись: {row} / {total} ")


# ============================================================
#  SearchPanel — Панель поиска и фильтрации
# ============================================================
class SearchPanel(QWidget):
    """Поле ввода + ComboBox выбора колонки + кнопки «Найти» / «Сброс».

    Параметры:
        model   — QSqlTableModel для фильтрации
        columns — [(display_name, db_column_name), ...]

    Сигналы:
        filter_applied — при применении фильтра (передаёт текст фильтра)
        filter_reset   — при сбросе фильтра
    """

    filter_applied = pyqtSignal(str)
    filter_reset = pyqtSignal()

    def __init__(self, model: QSqlTableModel, columns: list, parent=None):
        super().__init__(parent)
        self._model = model
        self._columns = columns
        self._base_filter = ""  # дополнительный фильтр (для master-detail)
        self._build()

    def _build(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        layout.addWidget(QLabel("🔍 Поиск:"))

        self._input = QLineEdit()
        self._input.setPlaceholderText("Введите значение для поиска...")
        self._input.returnPressed.connect(self._apply)
        self._input.setClearButtonEnabled(True)
        layout.addWidget(self._input, stretch=2)

        layout.addWidget(QLabel("в колонке:"))

        self._combo = QComboBox()
        for display, _ in self._columns:
            self._combo.addItem(display)
        layout.addWidget(self._combo)

        btn_find = QPushButton("Найти")
        btn_find.setToolTip("Применить фильтр (Enter)")
        btn_find.clicked.connect(self._apply)
        layout.addWidget(btn_find)

        btn_reset = QPushButton("Сброс")
        btn_reset.setToolTip("Сбросить фильтр")
        btn_reset.clicked.connect(self._reset)
        layout.addWidget(btn_reset)

    def _apply(self):
        val = self._input.text().strip()
        idx = self._combo.currentIndex()
        _, col = self._columns[idx]

        parts = []
        if self._base_filter:
            parts.append(self._base_filter)
        if val:
            # ILIKE для регистронезависимого поиска
            parts.append(f"\"{col}\"::text ILIKE '%{val}%'")

        filt = " AND ".join(parts) if parts else ""
        self._model.setFilter(filt)
        self._model.select()
        self.filter_applied.emit(filt)

    def _reset(self):
        self._input.clear()
        filt = self._base_filter if self._base_filter else ""
        self._model.setFilter(filt)
        self._model.select()
        self.filter_reset.emit()

    def set_base_filter(self, filt: str):
        """Установить базовый фильтр (для master-detail связи).
        При поиске он будет добавлен через AND."""
        self._base_filter = filt


# ============================================================
#  ReadOnlyDelegate — делегат для запрета редактирования колонок
# ============================================================
class ReadOnlyDelegate(QStyledItemDelegate):
    """Делегат, который запрещает редактирование.
    Используется для вычисляемых колонок (GENERATED, VIEW).

    Пример:
        view.setItemDelegateForColumn(4, ReadOnlyDelegate(view))
    """

    def createEditor(self, parent, option, index):
        return None  # Не создаём редактор → колонка read-only


_MONEY_DECIMAL_SEP = None


def _money_decimal_sep() -> str:
    """Возвращает десятичный разделитель, который ожидает/выдаёт
    PostgreSQL для типа MONEY в текущей сессии.

    Парсинг MONEY в PG зависит от lc_monetary: в ru_RU нужен `,`,
    в C/en_US — `.`. Жёстко захардкоденный разделитель приводит к
    тому, что либо строка отбрасывается с 22P02 invalid input
    syntax for type money, либо (что хуже) парсится как
    thousands-separator и молча искажает значение.

    Определяем разделитель один раз: кастуем numeric → money (numeric
    всегда парсится с точкой) и смотрим, какой символ PG вывел."""
    global _MONEY_DECIMAL_SEP
    if _MONEY_DECIMAL_SEP is not None:
        return _MONEY_DECIMAL_SEP
    q = QSqlQuery()
    if q.exec_("SELECT (1.5::numeric)::money::text") and q.next():
        txt = str(q.value(0) or "")
        _MONEY_DECIMAL_SEP = "," if "," in txt else "."
    else:
        _MONEY_DECIMAL_SEP = "."
    return _MONEY_DECIMAL_SEP


class MoneyDelegate(QStyledItemDelegate):
    """Делегат редактирования MONEY через float-редактор."""

    def createEditor(self, parent, option, index):
        editor = QDoubleSpinBox(parent)
        editor.setDecimals(2)
        editor.setMinimum(0.0)
        editor.setMaximum(1_000_000_000.0)
        editor.setSingleStep(1.0)
        return editor

    def setEditorData(self, editor, index):
        txt = str(index.model().data(index, Qt.EditRole) or "")
        cleaned = "".join(ch for ch in txt if ch.isdigit() or ch in ",.-")
        cleaned = cleaned.replace(",", ".")
        try:
            value = float(cleaned) if cleaned not in ("", "-", ".", "-.") else 0.0
        except ValueError:
            value = 0.0
        editor.setValue(value)

    def setModelData(self, editor, model, index):
        # PostgreSQL MONEY.cash_in читает десятичный разделитель из
        # lc_monetary. Формат должен совпадать с настройками сервера,
        # иначе PG вернёт 22P02 или, что опаснее, воспримет `.` / `,`
        # как разделитель тысяч и запишет искажённое значение.
        money_text = f"{editor.value():.2f}"
        sep = _money_decimal_sep()
        if sep != ".":
            money_text = money_text.replace(".", sep)
        model.setData(index, money_text, Qt.EditRole)


# ============================================================
#  StatusLabel — информационная метка со статусом
# ============================================================
class StatusLabel(QLabel):
    """Цветная метка для отображения статуса:
    success (зелёный), error (красный), info (синий)."""

    STYLES = {
        "success": "color: #2d6a4f; background: #d8f3dc; "
                   "border: 1px solid #95d5b2; border-radius: 4px; padding: 4px 8px;",
        "error":   "color: #9b2226; background: #fde8e8; "
                   "border: 1px solid #e5383b; border-radius: 4px; padding: 4px 8px;",
        "info":    "color: #2E4057; background: #d9e2ec; "
                   "border: 1px solid #9fb3c8; border-radius: 4px; padding: 4px 8px;",
    }

    def __init__(self, text="", status="info", parent=None):
        super().__init__(text, parent)
        self.set_status(status)
        self.setWordWrap(True)

    def set_status(self, status: str):
        self.setStyleSheet(self.STYLES.get(status, self.STYLES["info"]))

    def show_message(self, text: str, status: str = "info"):
        self.setText(text)
        self.set_status(status)
