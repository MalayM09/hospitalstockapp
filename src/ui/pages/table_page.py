"""
Base for list screens: search + filters + table + totals footer, with Excel
export and printing of exactly what is on screen (after search/filters).
"""
from datetime import date

from PyQt6.QtWidgets import QFileDialog, QHBoxLayout, QPushButton

from services.report_service import Report
from ui.pages.base import Page
from ui.printing import print_report
from ui.widgets import Card, DataTable, SearchBox, button, label, toast, uniform_height


class TablePage(Page):
    columns = []          # [(header, kind)]
    stretch_col = 0
    search_placeholder = "Search…"
    empty_text = "Nothing to show."
    sum_columns = ()      # indexes of columns to total in the footer

    def __init__(self, main):
        super().__init__(main)
        self.toolbar = QHBoxLayout()
        self.toolbar.setSpacing(8)
        self.search = SearchBox(self.search_placeholder)
        self.search.textChanged.connect(self._filter_changed)
        self.toolbar.addWidget(self.search)
        self.add_filters(self.toolbar)
        self.toolbar.addStretch()
        self.add_actions(self.toolbar)
        self.toolbar.addWidget(button("Export", None, "file-arrow-down", "Save as Excel", self.export))
        self.toolbar.addWidget(button("Print", None, "printer", "Print what is shown", self.print_))
        for i in range(self.toolbar.count()):  # buttons as tall as the search box
            w = self.toolbar.itemAt(i).widget()
            if isinstance(w, QPushButton):
                uniform_height(w)
        self.root.addLayout(self.toolbar)

        card = Card(margins=(14, 8, 14, 10), spacing=6)
        self.table = DataTable(self.columns, self.stretch_col, self.empty_text)
        self.table.activated.connect(self.on_activate)
        self.table.selection_changed.connect(self.on_selection)
        card.add(self.table, 1)
        self.footer = label("", "caption")
        card.add(self.footer)
        self.root.addWidget(card, 1)

    # hooks for subclasses
    def add_filters(self, bar):
        pass

    def add_actions(self, bar):
        pass

    def load(self):
        """Return (rows, ids)."""
        return [], []

    def report_title(self):
        return self.title

    def period_text(self):
        return ""

    def on_activate(self, row_id):
        pass

    def on_selection(self):
        pass

    # behaviour
    def refresh(self):
        rows, ids = self.load()
        self.table.set_rows(rows, ids)
        self._update_footer()

    def _filter_changed(self, text):
        self.table.set_filter_text(text)
        self._update_footer()

    def _update_footer(self):
        rows = self.table.visible_rows()
        parts = [f"{len(rows)} row{'s' if len(rows) != 1 else ''}"]
        from utils.formatting import format_cell
        for i in self.sum_columns:
            header, kind = self.columns[i]
            parts.append(f"{header}: {format_cell(sum((r[i] or 0) for r in rows), kind)}")
        self.footer.setText("   ·   ".join(parts))

    def current_report(self):
        rows = self.table.visible_rows()
        totals = None
        if self.sum_columns and rows:
            totals = ["Total"] + [""] * (len(self.columns) - 1)
            for i in self.sum_columns:
                totals[i] = round(sum((r[i] or 0) for r in rows), 2)
            totals = tuple(totals)
        cols = [(h, "text" if k == "status" else k) for h, k in self.columns]
        rows = [tuple({"out": "Out of stock", "low": "Low", "ok": "In stock"}.get(v, v)
                      if self.columns[i][1] == "status" else v for i, v in enumerate(r)) for r in rows]
        return Report(self.report_title(), cols, rows, totals, period=self.period_text())

    def export(self):
        report = self.current_report()
        if not report.rows:
            toast(self, "Nothing to export", "info")
            return
        name = f"{report.title.replace(' ', '_')}_{date.today():%Y-%m-%d}.xlsx"
        path, _ = QFileDialog.getSaveFileName(self, "Export to Excel", name, "Excel files (*.xlsx)")
        if not path:
            return
        if not path.lower().endswith(".xlsx"):
            path += ".xlsx"
        from services.export_service import export_report
        export_report(report, path)
        toast(self, "Exported to Excel")

    def print_(self):
        report = self.current_report()
        if not report.rows:
            toast(self, "Nothing to print", "info")
            return
        if print_report(self, report):
            toast(self, "Sent to printer")
