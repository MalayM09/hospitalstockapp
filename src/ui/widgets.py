"""
Reusable UI components (Clinical Teal). Screens are assembled from these so
that every page looks and behaves the same way.
"""
from datetime import date, timedelta

from PyQt6.QtCore import (
    QDate, QEasingCurve, QPropertyAnimation, QRectF, QSize, QSortFilterProxyModel, Qt, QTimer,
    pyqtSignal,
)
from PyQt6.QtGui import QAction, QBrush, QColor, QFont, QPainter, QPen, QStandardItem, QStandardItemModel
from PyQt6.QtWidgets import (
    QAbstractItemView, QComboBox, QCompleter, QDateEdit, QFrame, QGraphicsOpacityEffect, QHBoxLayout,
    QHeaderView, QLabel, QLineEdit, QMessageBox, QPushButton, QSizePolicy, QStyledItemDelegate,
    QTableView, QVBoxLayout, QWidget,
)

from ui.theme import COLORS, fs, icon
from utils.formatting import format_cell

# ---------------------------------------------------------------------------- basics


def uniform_height(widget):
    """Every text box, dropdown and date box gets the same height, so rows line up."""
    widget.setFixedHeight(fs(38))
    return widget


def repolish(w):
    w.style().unpolish(w)
    w.style().polish(w)


def label(text="", role=None, wrap=False):
    lb = QLabel(text)
    if role:
        lb.setProperty("role", role)
    lb.setWordWrap(wrap)
    return lb


def button(text, variant=None, icon_name=None, tooltip=None, callback=None):
    b = QPushButton(text)
    if variant:
        b.setProperty("variant", variant)
    if icon_name:
        color = "#FFFFFF" if variant in ("primary", "dangerSolid") else \
            COLORS["danger"] if variant == "danger" else COLORS["text"]
        b.setIcon(icon(icon_name, color))
        b.setIconSize(QSize(16, 16))
    if tooltip:
        b.setToolTip(tooltip)
    if callback:
        b.clicked.connect(callback)
    b.setCursor(Qt.CursorShape.PointingHandCursor)
    return b


class Card(QFrame):
    def __init__(self, margins=(18, 16, 18, 16), spacing=12, parent=None):
        super().__init__(parent)
        self.setProperty("role", "card")
        self.layout_ = QVBoxLayout(self)
        self.layout_.setContentsMargins(*margins)
        self.layout_.setSpacing(spacing)

    def add(self, widget_or_layout, stretch=0):
        if isinstance(widget_or_layout, QWidget):
            self.layout_.addWidget(widget_or_layout, stretch)
        else:
            self.layout_.addLayout(widget_or_layout, stretch)
        return widget_or_layout


def divider():
    d = QFrame()
    d.setProperty("role", "divider")
    return d


def hbox(*items, spacing=10, margins=(0, 0, 0, 0)):
    lay = QHBoxLayout()
    lay.setSpacing(spacing)
    lay.setContentsMargins(*margins)
    for it in items:
        if it is None:
            lay.addStretch()
        elif isinstance(it, QWidget):
            lay.addWidget(it)
        else:
            lay.addLayout(it)
    return lay


def icon_tile(icon_name, fg, bg, size=40):
    lb = QLabel()
    lb.setFixedSize(size, size)
    lb.setAlignment(Qt.AlignmentFlag.AlignCenter)
    lb.setPixmap(icon(icon_name, fg).pixmap(QSize(size // 2, size // 2)))
    lb.setStyleSheet(f"background:{bg}; border-radius:{min(10, size // 2)}px;")
    return lb


PILL_COLORS = {
    "out": ("Out of stock", COLORS["danger"], COLORS["danger_soft"]),
    "low": ("Low", COLORS["warning"], COLORS["warning_soft"]),
    "ok": ("In stock", COLORS["success"], COLORS["success_soft"]),
}


class PageHeader(QWidget):
    def __init__(self, title, subtitle=""):
        super().__init__()
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(10)
        text = QVBoxLayout()
        text.setSpacing(2)
        self.title = label(title, "pageTitle")
        self.subtitle = label(subtitle, "pageSub")
        text.addWidget(self.title)
        text.addWidget(self.subtitle)
        lay.addLayout(text)
        lay.addStretch()
        self._actions = lay

    def add_action(self, widget):
        self._actions.addWidget(widget)
        return widget


class KpiCard(Card):
    def __init__(self, icon_name, title, fg, bg):
        super().__init__(margins=(16, 14, 16, 14))
        row = QHBoxLayout()
        row.setSpacing(14)
        row.addWidget(icon_tile(icon_name, fg, bg, 44), alignment=Qt.AlignmentFlag.AlignTop)
        text = QVBoxLayout()
        text.setSpacing(1)
        text.addWidget(label(title, "kpiLabel"))
        self.value = label("—", "kpiValue")
        self.caption = label("", "caption")
        text.addWidget(self.value)
        text.addWidget(self.caption)
        row.addLayout(text)
        row.addStretch()
        self.add(row)

    def set(self, value, caption=""):
        self.value.setText(str(value))
        self.caption.setText(caption)


# ---------------------------------------------------------------------------- forms


class Field(QWidget):
    """Label + input + inline error message."""

    def __init__(self, caption, widget, hint=""):
        super().__init__()
        self.widget = widget
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(5)
        lay.addWidget(label(caption, "fieldLabel"))
        if isinstance(widget, (QLineEdit, QComboBox, QDateEdit)):
            uniform_height(widget)
        lay.addWidget(widget)
        self.error = label("", "fieldError")
        self.error.setVisible(False)
        self.hint = label(hint, "caption") if hint else None
        if self.hint:
            lay.addWidget(self.hint)
        lay.addWidget(self.error)

    def set_error(self, message=""):
        self.widget.setProperty("invalid", bool(message))
        repolish(self.widget)
        self.error.setText(message)
        self.error.setVisible(bool(message))
        if self.hint:
            self.hint.setVisible(not message)
        if message:
            self.widget.setFocus()


def line_edit(placeholder="", text=""):
    e = QLineEdit(text)
    e.setPlaceholderText(placeholder)
    e.setClearButtonEnabled(False)
    return e


class SearchBox(QLineEdit):
    def __init__(self, placeholder="Search…"):
        super().__init__()
        self.setPlaceholderText(placeholder)
        self.setClearButtonEnabled(True)
        self.addAction(QAction(icon("magnifying-glass", COLORS["faint"]), "", self),
                       QLineEdit.ActionPosition.LeadingPosition)
        self.setMinimumWidth(240)
        uniform_height(self)


class SearchCombo(QComboBox):
    """
    Dropdown you can type into: typing "glu" shows "Glucose Kit". Only an exact
    (case-insensitive) match of a list entry counts as a selection.
    """

    def __init__(self, placeholder="Type to search…"):
        super().__init__()
        self.setEditable(True)
        self.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.lineEdit().setPlaceholderText(placeholder)
        self.setMaxVisibleItems(14)
        comp = self.completer()
        comp.setFilterMode(Qt.MatchFlag.MatchContains)
        comp.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        comp.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setMinimumContentsLength(12)

    def set_items(self, rows, keep_selection=True):
        """rows: [(id, name)]"""
        current = self.current_id() if keep_selection else None
        self.blockSignals(True)
        self.clear()
        for row_id, name in rows:
            self.addItem(name, row_id)
        self.setCurrentIndex(-1)
        self.lineEdit().clear()
        self.blockSignals(False)
        if current is not None:
            self.set_current_id(current)

    def current_id(self):
        text = self.currentText().strip().lower()
        if not text:
            return None
        for i in range(self.count()):
            if self.itemText(i).lower() == text:
                return self.itemData(i)
        return None

    def set_current_id(self, row_id):
        idx = self.findData(row_id)
        self.setCurrentIndex(idx)
        if idx < 0:
            self.lineEdit().clear()

    def reset(self):
        self.setCurrentIndex(-1)
        self.lineEdit().clear()


def date_edit(value=None, max_today=True):
    d = QDateEdit(value or QDate.currentDate())
    d.setDisplayFormat("dd-MM-yyyy")
    d.setCalendarPopup(True)
    if max_today:
        d.setMaximumDate(QDate.currentDate())
    d.setMinimumDate(QDate(2000, 1, 1))
    return d


def iso(qdate):
    return qdate.toString("yyyy-MM-dd")


def qdate(iso_text):
    return QDate.fromString(iso_text[:10], "yyyy-MM-dd") if iso_text else QDate.currentDate()


class OptionalDateEdit(QDateEdit):
    """Date that can be empty ("No expiry"): the minimum date stands for 'none'."""

    NONE = QDate(2000, 1, 1)

    def __init__(self):
        super().__init__()
        self.setDisplayFormat("dd-MM-yyyy")
        self.setCalendarPopup(True)
        self.setMinimumDate(self.NONE)
        self.setSpecialValueText("No expiry")
        self.set_value(None)

    def value(self):
        return None if self.date() == self.NONE else iso(self.date())

    def set_value(self, iso_text):
        self.setDate(qdate(iso_text) if iso_text else self.NONE)


# ---------------------------------------------------------------------------- tables

RAW_ROLE = Qt.ItemDataRole.UserRole + 1
ID_ROLE = Qt.ItemDataRole.UserRole + 2
KIND_ROLE = Qt.ItemDataRole.UserRole + 3


class _FilterProxy(QSortFilterProxyModel):
    def __init__(self):
        super().__init__()
        self.text = ""
        self.predicate = None
        self.setSortRole(RAW_ROLE)
        self.setSortCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)

    def filterAcceptsRow(self, row, parent):
        model = self.sourceModel()
        if self.predicate:
            raw = [model.index(row, c, parent).data(RAW_ROLE) for c in range(model.columnCount())]
            if not self.predicate(raw):
                return False
        if not self.text:
            return True
        for c in range(model.columnCount()):
            v = model.index(row, c, parent).data(Qt.ItemDataRole.DisplayRole)
            if v and self.text in str(v).lower():
                return True
        return False

    def lessThan(self, left, right):
        a, b = left.data(RAW_ROLE), right.data(RAW_ROLE)
        if a is None or b is None:
            return (a is None) and (b is not None)
        if isinstance(a, (int, float)) and isinstance(b, (int, float)):
            return a < b
        return str(a).lower() < str(b).lower()


class _PillDelegate(QStyledItemDelegate):
    def paint(self, painter, option, index):
        super().paint(painter, option, index)  # background / selection
        key = index.data(RAW_ROLE)
        if key not in PILL_COLORS:
            return
        text, fg, bg = PILL_COLORS[key]
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        f = QFont(option.font)
        f.setPixelSize(fs(11))
        f.setWeight(QFont.Weight.DemiBold)
        painter.setFont(f)
        w = painter.fontMetrics().horizontalAdvance(text) + 20
        h = fs(11) + 10
        r = option.rect
        rect = QRectF(r.x() + 8, r.y() + (r.height() - h) / 2, w, h)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(QColor(bg)))
        painter.drawRoundedRect(rect, h / 2, h / 2)
        painter.setPen(QPen(QColor(fg)))
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, text)
        painter.restore()

    def displayText(self, value, locale):
        return ""


class DataTable(QWidget):
    """
    Sortable, filterable table. Columns: [(header, kind)] where kind is one of
    text, int, money, date, month, pct, status. Rows: list of tuples; ids give
    each row an identity for selection / double-click.
    """
    activated = pyqtSignal(object)        # row id (double-click / Enter)
    selection_changed = pyqtSignal()

    def __init__(self, columns, stretch_col=0, empty_text="Nothing to show yet."):
        super().__init__()
        self.columns = columns
        self.model = QStandardItemModel(0, len(columns))
        self.model.setHorizontalHeaderLabels([h for h, _ in columns])
        self.proxy = _FilterProxy()
        self.proxy.setSourceModel(self.model)

        self.view = QTableView()
        self.view.setModel(self.proxy)
        # No sort until the user clicks a header: rows keep the order they were given
        self.view.horizontalHeader().setSortIndicator(-1, Qt.SortOrder.AscendingOrder)
        self.view.setSortingEnabled(True)
        self.view.setShowGrid(False)
        self.view.setWordWrap(False)
        self.view.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.view.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.view.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.view.verticalHeader().setVisible(False)
        self.view.verticalHeader().setDefaultSectionSize(fs(38))
        self.view.setHorizontalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.view.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.view.setMouseTracking(True)
        hv = self.view.horizontalHeader()
        hv.setHighlightSections(False)
        hv.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        for col in (stretch_col if isinstance(stretch_col, (tuple, list)) else (stretch_col,)):
            hv.setSectionResizeMode(col, QHeaderView.ResizeMode.Stretch)
        hv.setDefaultAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        for i, (_, kind) in enumerate(columns):
            if kind == "status":
                self.view.setItemDelegateForColumn(i, _PillDelegate(self.view))
                hv.setSectionResizeMode(i, QHeaderView.ResizeMode.Fixed)
                self.view.setColumnWidth(i, fs(120))
        self.view.doubleClicked.connect(self._on_double_click)
        self.view.selectionModel().selectionChanged.connect(lambda *_: self.selection_changed.emit())

        self.empty = label(empty_text, "muted")
        self.empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty.setVisible(False)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        lay.addWidget(self.view)
        lay.addWidget(self.empty)

    def set_rows(self, rows, ids=None):
        sort_col = self.view.horizontalHeader().sortIndicatorSection()
        sort_order = self.view.horizontalHeader().sortIndicatorOrder()
        selected = self.selected_id()
        self.view.setSortingEnabled(False)
        self.model.removeRows(0, self.model.rowCount())
        right = Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        left = Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
        for n, row in enumerate(rows):
            items = []
            for value, (_, kind) in zip(row, self.columns):
                it = QStandardItem("" if kind == "status" else format_cell(value, kind))
                it.setData(value, RAW_ROLE)
                it.setData(ids[n] if ids else n, ID_ROLE)
                it.setTextAlignment(right if kind in ("int", "money", "pct") else left)
                if kind == "money" and isinstance(value, (int, float)) and value < 0:
                    it.setForeground(QColor(COLORS["danger"]))
                items.append(it)
            self.model.appendRow(items)
        if sort_col >= 0:
            self.view.setSortingEnabled(True)
            self.view.sortByColumn(sort_col, sort_order)
        else:
            self.proxy.sort(-1)
            self.view.horizontalHeader().setSortIndicator(-1, Qt.SortOrder.AscendingOrder)
            self.view.setSortingEnabled(True)
        self._update_empty()
        if selected is not None:
            self.select_id(selected)

    def set_filter_text(self, text):
        self.proxy.text = (text or "").strip().lower()
        self.proxy.invalidateFilter()
        self._update_empty()

    def set_predicate(self, fn):
        self.proxy.predicate = fn
        self.proxy.invalidateFilter()
        self._update_empty()

    def _update_empty(self):
        empty = self.proxy.rowCount() == 0
        self.empty.setVisible(empty)
        self.view.setVisible(not empty)

    def visible_rows(self):
        """Raw values of the rows currently shown, in display order."""
        out = []
        for r in range(self.proxy.rowCount()):
            out.append(tuple(self.proxy.index(r, c).data(RAW_ROLE) for c in range(self.proxy.columnCount())))
        return out

    def selected_id(self):
        idx = self.view.selectionModel().selectedRows()
        return idx[0].data(ID_ROLE) if idx else None

    def select_id(self, row_id):
        for r in range(self.proxy.rowCount()):
            if self.proxy.index(r, 0).data(ID_ROLE) == row_id:
                self.view.selectRow(r)
                return

    def _on_double_click(self, index):
        self.activated.emit(index.data(ID_ROLE))

    def keyPressEvent(self, e):
        if e.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter) and self.selected_id() is not None:
            self.activated.emit(self.selected_id())
            return
        super().keyPressEvent(e)


# ---------------------------------------------------------------------------- date ranges


def financial_year_start(today):
    """Indian financial year starts on 1 April."""
    return date(today.year if today.month >= 4 else today.year - 1, 4, 1)


def months_before(first_of_month, n):
    """First day of the month n months before the given first-of-month."""
    y, m = divmod(first_of_month.year * 12 + first_of_month.month - 1 - n, 12)
    return date(y, m + 1, 1)


class DateRangeBar(QWidget):
    """Quick ranges (This month, Last month, This financial year…) plus From/To."""
    changed = pyqtSignal(str, str)

    RANGES = ["This month", "Last month", "Last 3 months", "This financial year",
              "Last financial year", "All time", "Custom"]

    def __init__(self, default="This month"):
        super().__init__()
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(8)
        self.quick = uniform_height(QComboBox())
        self.quick.addItems(self.RANGES)
        self.start = uniform_height(date_edit())
        self.end = uniform_height(date_edit())
        lay.addWidget(self.quick)
        lay.addWidget(self.start)
        lay.addWidget(label("to", "muted"))
        lay.addWidget(self.end)
        self.quick.currentTextChanged.connect(self._apply_quick)
        self.start.dateChanged.connect(self._manual)
        self.end.dateChanged.connect(self._manual)
        self._applying = False
        self.quick.setCurrentText(default)
        self._apply_quick(default)

    def _apply_quick(self, name):
        today = date.today()
        first = today.replace(day=1)
        ranges = {
            "This month": (first, today),
            "Last month": ((first - timedelta(days=1)).replace(day=1), first - timedelta(days=1)),
            "Last 3 months": (months_before(first, 2), today),
            "This financial year": (financial_year_start(today), today),
            "Last financial year": (financial_year_start(today).replace(year=financial_year_start(today).year - 1),
                                    financial_year_start(today) - timedelta(days=1)),
            "All time": (date(2000, 1, 1), today),
        }
        if name not in ranges:
            return
        s, e = ranges[name]
        self._applying = True
        self.start.setDate(QDate(s.year, s.month, s.day))
        self.end.setDate(QDate(e.year, e.month, e.day))
        self._applying = False
        self._emit()

    def _manual(self):
        if self._applying:
            return
        if self.start.date() > self.end.date():
            self.end.setDate(self.start.date())
        self.quick.blockSignals(True)
        self.quick.setCurrentText("Custom")
        self.quick.blockSignals(False)
        self._emit()

    def _emit(self):
        self.changed.emit(*self.range())

    def range(self):
        return iso(self.start.date()), iso(self.end.date())

    def period_text(self):
        s, e = self.start.date(), self.end.date()
        if self.quick.currentText() == "All time":
            return "All time"
        return f"{s.toString('dd MMM yyyy')} to {e.toString('dd MMM yyyy')}"


# ---------------------------------------------------------------------------- feedback


class Toast(QLabel):
    """Small message that appears at the bottom of the window and fades away."""

    COLORS_BY_KIND = {"success": COLORS["accent"], "error": COLORS["danger"], "info": "#111827"}

    def __init__(self, parent, message, kind="success", msec=2600):
        super().__init__(message, parent)
        self.setStyleSheet(f"background:{self.COLORS_BY_KIND.get(kind, '#111827')}; color:white;"
                           f"border-radius:8px; padding:10px 18px; font-weight:600;")
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.adjustSize()
        self._place()
        self.effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self.effect)
        self.show()
        self.raise_()
        self.anim = QPropertyAnimation(self.effect, b"opacity", self)
        self.anim.setDuration(400)
        self.anim.setStartValue(1.0)
        self.anim.setEndValue(0.0)
        self.anim.setEasingCurve(QEasingCurve.Type.InQuad)
        self.anim.finished.connect(self.deleteLater)
        QTimer.singleShot(msec, self.anim.start)

    def _place(self):
        p = self.parentWidget()
        self.move((p.width() - self.width()) // 2, p.height() - self.height() - 28)


def toast(widget, message, kind="success"):
    Toast(widget.window(), message, kind)


def confirm(parent, title, text, ok_text="Delete", danger=True):
    box = QMessageBox(parent)
    box.setWindowTitle(title)
    box.setText(f"<b>{title}</b>")
    box.setInformativeText(text)
    box.setIcon(QMessageBox.Icon.Warning if danger else QMessageBox.Icon.Question)
    ok = box.addButton(ok_text, QMessageBox.ButtonRole.AcceptRole)
    ok.setProperty("variant", "dangerSolid" if danger else "primary")
    cancel = box.addButton("Cancel", QMessageBox.ButtonRole.RejectRole)
    box.setDefaultButton(cancel)
    box.exec()
    return box.clickedButton() is ok


def alert(parent, title, text, kind="warning"):
    icon_kind = {"warning": QMessageBox.Icon.Warning, "error": QMessageBox.Icon.Critical,
                 "info": QMessageBox.Icon.Information}[kind]
    box = QMessageBox(icon_kind, title, text, QMessageBox.StandardButton.Ok, parent)
    box.exec()
