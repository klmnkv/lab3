"""
widget.py — Переиспользуемые виджеты для приложения educationDB.

Содержит:
  - NavigationToolbar  — аналог BindingNavigator (Windows Forms)
  - SearchPanel        — панель поиска и фильтрации
  - ReadOnlyDelegate   — делегат для блокировки редактирования отдельных колонок
  - StatusLabel         — метка для отображения статуса подключения
"""

from PyQt5.QtWidgets import (
    QWidget, QHBoxLayout, QTableView, QLabel, QLineEdit,
    QComboBox, QPushButton, QToolBar, QAction, QMessageBox,
    QStyledItemDelegate, QAbstractItemView
)
from PyQt5.QtSql import QSqlTableModel
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

    def __init__(self, view: QTableView, model: QSqlTableModel, parent=None):
        super().__init__("Навигация", parent)
        self._view = view
        self._model = model
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

    # --- CRUD ---
    def _add(self):
        row = self._model.rowCount()
        self._model.insertRow(row)
        self._view.selectRow(row)
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
        if not self._model.submitAll():
            error_text = self._model.lastError().text()
            QMessageBox.critical(self, "Ошибка сохранения", error_text)
            self._model.revertAll()
            self.record_error.emit(error_text)
        else:
            self.record_saved.emit()

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
