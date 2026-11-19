from datetime import date

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QFileDialog, QFrame, QHBoxLayout, QVBoxLayout

from services.report_service import REPORTS, run_report
from ui.pages.base import Page
from ui.printing import print_report
from ui.theme import COLORS
from ui.widgets import Card, DataTable, DateRangeBar, button, label, toast
from utils.formatting import format_cell


class ReportEntry(QFrame):
    """One clickable report in the left column: bold name + grey description."""
    clicked = pyqtSignal(str)

    def __init__(self, key, name, desc):
        super().__init__()
        self.key = key
        self.setObjectName("reportEntry")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(12, 8, 10, 8)
        lay.setSpacing(2)
        lay.addWidget(label(name, "strong"))
        lay.addWidget(label(desc, "caption", wrap=True))
        self.set_selected(False)

    def set_selected(self, selected):
        bg = COLORS["accent_soft"] if selected else "transparent"
        hover = COLORS["accent_soft"] if selected else COLORS["row_hover"]
        self.setStyleSheet(f"#reportEntry {{ background:{bg}; border-radius:8px; }}"
                           f"#reportEntry:hover {{ background:{hover}; }}")

    def mousePressEvent(self, e):
        self.clicked.emit(self.key)

    def keyPressEvent(self, e):
        if e.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter, Qt.Key.Key_Space):
            self.clicked.emit(self.key)
        else:
            super().keyPressEvent(e)


class ReportsPage(Page):
    nav_key = "reports"
    title = "Reports"
    subtitle = "Pick a report and a period · export to Excel or print"

    def __init__(self, main):
        super().__init__(main)
        self.report = None
        self.header.add_action(button("Export", None, "file-arrow-down", "Save as Excel", self.export))
        self.header.add_action(button("Print", None, "printer", "Print this report", self.print_))

        bar = QHBoxLayout()
        bar.addWidget(label("Period", "fieldLabel"))
        self.range = DateRangeBar("This month")
        bar.addWidget(self.range)
        bar.addStretch()
        self.root.addLayout(bar)

        body = QHBoxLayout()
        body.setSpacing(16)
        pick = Card(margins=(10, 12, 10, 12), spacing=6)
        pick.setFixedWidth(270)
        pick.add(label("  REPORTS", "section"))
        self.entries = {}
        for key, name, desc in REPORTS:
            entry = ReportEntry(key, name, desc)
            entry.clicked.connect(self.select)
            self.entries[key] = entry
            pick.add(entry)
        pick.layout_.addStretch()
        self.current_key = None
        body.addWidget(pick)

        self.result = Card(margins=(18, 16, 18, 12), spacing=8)
        self.r_title = label("", "cardTitle")
        self.r_period = label("", "caption")
        self.result.add(self.r_title)
        self.result.add(self.r_period)
        self.table_holder = QHBoxLayout()
        self.result.add(self.table_holder, 1)
        self.totals = label("", "strong")
        self.totals.setWordWrap(True)
        self.note = label("", "caption", wrap=True)
        self.result.add(self.totals)
        self.result.add(self.note)
        body.addWidget(self.result, 1)
        self.root.addLayout(body, 1)

        self.table = None
        self.range.changed.connect(lambda *_: self.refresh())
        self.select(REPORTS[0][0])

    def select(self, key):
        self.current_key = key
        for k, entry in self.entries.items():
            entry.set_selected(k == key)
        self.refresh()

    def refresh(self):
        if not self.current_key:
            return
        start, end = self.range.range()
        self.report = run_report(self.current_key, start, end)
        r = self.report
        if self.range.quick.currentText() == "All time":
            r.period = "All time"
        self.r_title.setText(r.title)
        self.r_period.setText(r.period)
        if self.table is not None:
            self.table.setParent(None)
            self.table.deleteLater()
        self.table = DataTable(r.columns, 0, "No data for this period.")
        self.table_holder.addWidget(self.table)
        self.table.set_rows(r.rows)
        if r.totals and r.rows:
            parts = [f"{h}: {format_cell(v, k)}" for (h, k), v in zip(r.columns[1:], r.totals[1:])
                     if v not in ("", None)]
            self.totals.setText("Total  ·  " + "   ·   ".join(parts))
        else:
            self.totals.setText("")
        self.note.setText(r.note)

    def export(self):
        if not self.report or not self.report.rows:
            toast(self, "Nothing to export for this period", "info")
            return
        name = f"{self.report.title.replace(' ', '_')}_{date.today():%Y-%m-%d}.xlsx"
        path, _ = QFileDialog.getSaveFileName(self, "Export report", name, "Excel files (*.xlsx)")
        if path:
            if not path.lower().endswith(".xlsx"):
                path += ".xlsx"
            from services.export_service import export_report
            export_report(self.report, path)
            toast(self, "Report exported")

    def print_(self):
        if not self.report or not self.report.rows:
            toast(self, "Nothing to print for this period", "info")
            return
        if print_report(self, self.report):
            toast(self, "Sent to printer")
