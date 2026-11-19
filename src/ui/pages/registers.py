"""Stock Register, Issue Register and Bills screens."""
from PyQt6.QtWidgets import QPushButton, QButtonGroup, QHBoxLayout, QWidget

from services.bill_service import BillService
from services.stock_service import StockError, StockService, stock_status
from ui.pages.table_page import TablePage
from ui.widgets import DateRangeBar, alert, button, confirm, toast
from utils.formatting import inr, nice_date, qty


class Segmented(QWidget):
    """Row of toggle buttons (one checked)."""

    def __init__(self, options, on_change):
        super().__init__()
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        self.group = QButtonGroup(self)
        for i, (key, text) in enumerate(options):
            b = QPushButton(text)
            b.setCheckable(True)
            b.setProperty("variant", "segment")
            b.setProperty("key", key)
            if i == 0:
                b.setChecked(True)
            self.group.addButton(b)
            lay.addWidget(b)
        self.group.buttonClicked.connect(lambda b: on_change(b.property("key")))


class StockRegisterPage(TablePage):
    nav_key = "stock"
    title = "Stock Register"
    subtitle = "Current balance of every item · double-click an item for its full history"
    columns = [("Item", "text"), ("Received", "int"), ("Issued", "int"), ("Balance", "int"), ("Status", "status")]
    search_placeholder = "Search items…"
    empty_text = "No items match."

    def add_filters(self, bar):
        self.status_filter = "all"
        bar.addWidget(Segmented([("all", "All"), ("low", "Low"), ("out", "Out of stock"), ("in", "In stock")],
                                self._set_status))

    def _set_status(self, key):
        self.status_filter = key
        preds = {
            "all": None,
            "low": lambda r: r[4] == "low",
            "out": lambda r: r[4] == "out",
            "in": lambda r: r[3] > 0,
        }
        self.table.set_predicate(preds[key])
        self._update_footer()

    def load(self):
        rows = StockService().get_stock_register_view()
        return ([(r["name"], r["received"], r["issued"], r["balance"], stock_status(r["balance"])) for r in rows],
                [r["id"] for r in rows])

    def report_title(self):
        return "Stock Register" + ({"low": " — Low stock", "out": " — Out of stock", "in": " — In stock"}
                                   .get(self.status_filter, ""))

    def on_activate(self, item_id):
        self.main.show_item_ledger(item_id)


class IssueRegisterPage(TablePage):
    nav_key = "issues"
    title = "Issue Register"
    subtitle = "Every issue of stock · double-click to correct an entry"
    columns = [("Date", "date"), ("Item", "text"), ("Qty", "int"), ("Issued to / remarks", "text")]
    stretch_col = 1
    search_placeholder = "Search item or remarks…"
    empty_text = "No issues in this period."
    sum_columns = (2,)

    def add_filters(self, bar):
        self.range = DateRangeBar("This month")
        self.range.changed.connect(lambda *_: self.refresh())
        bar.addWidget(self.range)

    def add_actions(self, bar):
        bar.addWidget(button("Edit", None, "pencil-simple", "Correct the selected entry",
                             lambda: self.on_activate(self.table.selected_id())))
        bar.addWidget(button("Delete", "danger", "trash", "Delete the selected entry", self.delete_selected))

    def load(self):
        s, e = self.range.range()
        rows = StockService().get_stock_issuance_history(s, e)
        return ([(r["date"], r["item_name"], r["issued_qty"], r["remarks"]) for r in rows],
                [r["sr_no"] for r in rows])

    def period_text(self):
        return self.range.period_text()

    def on_activate(self, stock_id):
        if stock_id is None:
            toast(self, "Select an entry first", "info")
            return
        from ui.dialogs import EditIssueDialog
        if EditIssueDialog(stock_id, self).exec():
            toast(self, "Issue entry updated")

    def delete_selected(self):
        stock_id = self.table.selected_id()
        if stock_id is None:
            toast(self, "Select an entry first", "info")
            return
        svc = StockService()
        e = svc.get_issue(stock_id)
        if not e:
            return self.refresh()
        if confirm(self, "Delete issue entry?",
                   f"{nice_date(e['date'])} · {e['item_name']} · {qty(e['issued_qty'])} units\n\n"
                   "The quantity goes back into stock."):
            try:
                svc.delete_issue(stock_id)
            except StockError as err:
                alert(self, "Cannot delete", str(err))
                return
            toast(self, "Issue entry deleted")


class BillsPage(TablePage):
    nav_key = "bills"
    title = "Bills"
    subtitle = "Every purchase line · double-click to correct a line"
    columns = [("Date", "date"), ("Invoice", "text"), ("Vendor", "text"), ("Item", "text"), ("Batch", "text"),
               ("Expiry", "date"), ("Qty", "int"), ("Rate", "money"), ("GST", "pct"), ("Tax", "money"),
               ("Net", "money")]
    stretch_col = (2, 3)
    search_placeholder = "Search vendor, item, invoice…"
    empty_text = "No purchases in this period."
    sum_columns = (9, 10)

    def add_filters(self, bar):
        self.range = DateRangeBar("This month")
        self.range.changed.connect(lambda *_: self.refresh())
        bar.addWidget(self.range)

    def add_actions(self, bar):
        bar.addWidget(button("Edit", None, "pencil-simple", "Correct the selected line",
                             lambda: self.on_activate(self.table.selected_id())))
        bar.addWidget(button("Delete", "danger", "trash", "Delete the selected line", self.delete_selected))

    def load(self):
        s, e = self.range.range()
        rows = BillService().list_bills(s, e)
        return ([(r["date"], r["invoice_number"], r["vendor"], r["item"], r["batch"], r["expiry"] or None,
                  r["quantity"], r["rate"], r["gst_rate"], r["tax"], r["net_amount"]) for r in rows],
                [r["id"] for r in rows])

    def period_text(self):
        return self.range.period_text()

    def on_activate(self, bill_id):
        if bill_id is None:
            toast(self, "Select a bill line first", "info")
            return
        from ui.dialogs import EditBillDialog
        if EditBillDialog(bill_id, self).exec():
            toast(self, "Bill updated")

    def delete_selected(self):
        bill_id = self.table.selected_id()
        if bill_id is None:
            toast(self, "Select a bill line first", "info")
            return
        svc = BillService()
        b = svc.get_bill_by_id(bill_id)
        if not b:
            return self.refresh()
        if confirm(self, "Delete this bill line?",
                   f"Invoice {b['invoice_number']} · {b['vendor_name']}\n{b['item_name'] or '-'} × "
                   f"{qty(b['quantity'])} · {inr(b['net_amount'])}\n\nThe stock it added is removed too."):
            try:
                svc.delete_bill(bill_id)
            except StockError as err:
                alert(self, "Cannot delete", str(err))
                return
            toast(self, "Bill line deleted")
