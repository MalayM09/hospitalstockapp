from PyQt6.QtCore import QDate
from PyQt6.QtWidgets import QComboBox, QGridLayout, QHBoxLayout

from services.item_service import ItemService
from services.stock_service import StockError, StockService
from ui.pages.base import Page
from ui.theme import COLORS
from ui.widgets import Card, DataTable, Field, SearchCombo, button, date_edit, iso, label, line_edit, toast
from utils.formatting import nice_date, qty


class IssuePage(Page):
    nav_key = "issue"
    title = "Stock Issue"
    subtitle = "Record stock taken out of the store for use"

    def __init__(self, main):
        super().__init__(main)
        self.stock, self.items = StockService(), ItemService()
        self.header.add_action(button("Issue register", None, "clipboard-text",
                                      callback=lambda: main.navigate("issues")))

        body = QHBoxLayout()
        body.setSpacing(16)

        form = Card(margins=(22, 18, 22, 18), spacing=12)
        form.setFixedWidth(420)
        form.add(label("Issue stock", "cardTitle"))
        self.item = SearchCombo("Type item name…")
        self.f_item = Field("Item", self.item)
        form.add(self.f_item)

        self.balance = label("Choose an item to see its balance.")
        self.balance.setWordWrap(True)
        self._style_balance(None)
        form.add(self.balance)

        g = QGridLayout()
        g.setHorizontalSpacing(12)
        self.qty = line_edit("0")
        self.f_qty = Field("Quantity", self.qty)
        self.date = date_edit()
        g.addWidget(self.f_qty, 0, 0)
        g.addWidget(Field("Issue date", self.date), 0, 1)
        form.add(g)

        self.remarks = QComboBox()
        self.remarks.setEditable(True)
        self.remarks.lineEdit().setPlaceholderText("e.g. Lab, OPD, Ward (optional)")
        form.add(Field("Issued to / remarks", self.remarks))

        self.issue_btn = button("Issue stock", "primary", "export", "Issue (Ctrl+S or Enter)", self.on_save)
        form.add(self.issue_btn)
        hint = label("Date and 'issued to' stay filled in for the next entry.", "caption", wrap=True)
        form.add(hint)
        form.layout_.addStretch()
        body.addWidget(form)

        recent = Card(margins=(18, 16, 18, 8))
        recent.add(label("Recent issues", "cardTitle"))
        self.table = DataTable([("Date", "date"), ("Item", "text"), ("Qty", "int"), ("Issued to / remarks", "text")],
                               stretch_col=1, empty_text="No issues recorded yet.")
        self.table.activated.connect(lambda _id: main.navigate("issues"))
        recent.add(self.table, 1)
        body.addWidget(recent, 1)
        self.root.addLayout(body, 1)

        self.item.currentIndexChanged.connect(self.update_balance)
        self.item.lineEdit().textEdited.connect(lambda _t: self.update_balance())
        self.date.dateChanged.connect(self.update_balance)
        self.item.lineEdit().returnPressed.connect(self.qty.setFocus)
        self.qty.returnPressed.connect(self.on_save)

    def _style_balance(self, level):
        fg, bg = {
            None: (COLORS["muted"], COLORS["bg"]),
            "ok": (COLORS["accent"], COLORS["accent_soft"]),
            "low": (COLORS["warning"], COLORS["warning_soft"]),
            "out": (COLORS["danger"], COLORS["danger_soft"]),
        }[level]
        self.balance.setStyleSheet(f"background:{bg}; color:{fg}; border-radius:8px; padding:12px 14px;"
                                   f"font-weight:600;")

    def refresh(self):
        self.item.set_items([(i["id"], i["name"]) for i in self.items.get_all()])
        current = self.remarks.currentText()
        self.remarks.clear()
        self.remarks.addItems(self.stock.recent_remarks())
        self.remarks.setCurrentText(current)
        rows = self.stock.get_recent_issues(40)
        self.table.set_rows([(r["date"], r["item_name"], r["issued_qty"], r["remarks"] or "") for r in rows],
                            ids=[r["id"] for r in rows])
        self.update_balance()

    def update_balance(self):
        from services.stock_service import stock_status
        item_id = self.item.current_id()
        if not item_id:
            self.balance.setText("Choose an item to see its balance.")
            self._style_balance(None)
            return
        now = self.stock.get_stock_balance(item_id)
        text = f"Available now: {qty(now)} units"
        level = stock_status(now)
        if self.date.date() != QDate.currentDate():
            on_date = self.stock.get_stock_balance(item_id, as_of=iso(self.date.date()))
            text += f"\nOn {nice_date(iso(self.date.date()))}: {qty(on_date)} units"
            level = stock_status(min(now, on_date))
        self.balance.setText(text)
        self._style_balance(level)

    def on_save(self):
        item_id = self.item.current_id()
        self.f_item.set_error("" if item_id else "Choose an item from the list.")
        q = self.qty.text().strip()
        if not q.isdigit() or int(q) <= 0:
            self.f_qty.set_error("Enter a whole number above 0.")
            return
        self.f_qty.set_error()
        if not item_id:
            return
        try:
            self.stock.issue_stock(item_id, int(q), issue_date=iso(self.date.date()),
                                   remarks=self.remarks.currentText().strip())
        except StockError as e:
            self.f_qty.set_error(str(e).split("\n")[0])
            return
        toast(self, f"Issued {q} × {self.item.currentText()}")
        self.qty.clear()
        self.item.reset()
        self.item.setFocus()
        self.refresh()

    def on_escape(self):
        self.qty.clear()
        self.item.reset()
        self.f_item.set_error()
        self.f_qty.set_error()
        self.update_balance()
