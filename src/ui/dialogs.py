"""Dialogs: edit bill line, edit issue, name input, change password, item history."""
from PyQt6.QtWidgets import QComboBox, QDialog, QGridLayout, QHBoxLayout, QLineEdit, QVBoxLayout

from services.bill_service import BillService
from services.gst import GST_RATES, line_totals
from services.item_service import ItemService
from services.stock_service import StockError, StockService
from services.vendor_service import VendorService
from ui.widgets import (
    DataTable, Field, OptionalDateEdit, SearchCombo, button, date_edit, iso, label, line_edit, qdate,
)
from utils.formatting import inr, qty


class FormDialog(QDialog):
    """Title, form area, Cancel + primary button. Subclasses implement save() -> bool."""

    def __init__(self, title, primary_text="Save", parent=None, width=520):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumWidth(width)
        self.lay = QVBoxLayout(self)
        self.lay.setContentsMargins(24, 20, 24, 18)
        self.lay.setSpacing(12)
        self.lay.addWidget(label(title, "cardTitle"))
        self.form = QGridLayout()
        self.form.setHorizontalSpacing(14)
        self.form.setVerticalSpacing(8)
        self.lay.addLayout(self.form)
        self.error = label("", "fieldError", wrap=True)
        self.error.setVisible(False)
        self.lay.addWidget(self.error)
        row = QHBoxLayout()
        row.addStretch()
        row.addWidget(button("Cancel", callback=self.reject))
        self.primary = button(primary_text, "primary", callback=self._on_primary)
        self.primary.setDefault(True)
        row.addWidget(self.primary)
        self.lay.addLayout(row)

    def set_error(self, message):
        self.error.setText(message)
        self.error.setVisible(bool(message))
        # Reserve the wrapped text's real height, then re-fit the dialog
        inner = self.width() - self.lay.contentsMargins().left() - self.lay.contentsMargins().right()
        self.error.setMinimumHeight(self.error.heightForWidth(inner) if message else 0)
        self.adjustSize()

    def _on_primary(self):
        self.set_error("")
        if self.save():
            self.accept()

    def save(self):
        return True


class NameDialog(FormDialog):
    """Single text field (add / rename item or vendor). Caller saves; use value()."""

    def __init__(self, title, caption, value="", parent=None):
        super().__init__(title, "Save", parent, width=420)
        self.edit = line_edit(caption, value)
        self.form.addWidget(Field(caption, self.edit), 0, 0)
        self.edit.selectAll()

    def value(self):
        return self.edit.text()


class ChangePasswordDialog(FormDialog):
    def __init__(self, username, parent=None):
        super().__init__("Change password", "Change password", parent, width=420)
        self.username = username
        self.current, self.new, self.repeat = QLineEdit(), QLineEdit(), QLineEdit()
        for i, (cap, w) in enumerate([("Current password", self.current), ("New password", self.new),
                                      ("Repeat new password", self.repeat)]):
            w.setEchoMode(QLineEdit.EchoMode.Password)
            self.form.addWidget(Field(cap, w), i, 0)

    def save(self):
        from services.user_service import UserService
        if self.new.text() != self.repeat.text():
            self.set_error("The new passwords don't match.")
            return False
        try:
            UserService().change_password(self.username, self.current.text(), self.new.text())
        except ValueError as e:
            self.set_error(str(e))
            return False
        return True


class EditIssueDialog(FormDialog):
    def __init__(self, stock_id, parent=None):
        super().__init__("Edit issue entry", "Save changes", parent, width=460)
        self.stock = StockService()
        self.stock_id = stock_id
        e = self.stock.get_issue(stock_id)
        self.item = SearchCombo()
        self.item.set_items([(i["id"], i["name"]) for i in ItemService().get_all()], keep_selection=False)
        self.item.set_current_id(e["item_id"])
        self.qty = line_edit("0", str(e["issued_qty"]))
        self.date = date_edit(qdate(e["date"]))
        self.remarks = line_edit("Optional", e.get("remarks") or "")
        self.form.addWidget(Field("Item", self.item), 0, 0, 1, 2)
        self.form.addWidget(Field("Quantity", self.qty), 1, 0)
        self.form.addWidget(Field("Issue date", self.date), 1, 1)
        self.form.addWidget(Field("Issued to / remarks", self.remarks), 2, 0, 1, 2)

    def save(self):
        item_id = self.item.current_id()
        q = self.qty.text().strip()
        if not item_id:
            self.set_error("Choose an item from the list.")
            return False
        if not q.isdigit() or int(q) <= 0:
            self.set_error("Quantity must be a whole number above 0.")
            return False
        try:
            self.stock.update_issue(self.stock_id, item_id, int(q), iso(self.date.date()), self.remarks.text().strip())
        except StockError as e:
            self.set_error(str(e))
            return False
        return True


class EditBillDialog(FormDialog):
    """Edit one bill line; taxes recalculate live."""

    def __init__(self, bill_id, parent=None):
        super().__init__("Edit bill line", "Save changes", parent, width=600)
        self.bills = BillService()
        self.bill_id = bill_id
        b = self.bills.get_bill_by_id(bill_id)
        self.item = SearchCombo()
        self.item.set_items([(i["id"], i["name"]) for i in ItemService().get_all()], keep_selection=False)
        self.item.set_current_id(b["item_id"])
        self.vendor = SearchCombo()
        self.vendor.set_items([(v["id"], v["name"]) for v in VendorService().get_all()], keep_selection=False)
        self.vendor.set_current_id(b["vendor_id"])
        self.invoice = line_edit("", b["invoice_number"] or "")
        self.date = date_edit(qdate(b["invoice_date"] or b["entry_date"]))
        self.batch = line_edit("Optional", b["batch_number"] or "")
        self.expiry = OptionalDateEdit()
        self.expiry.set_value(b.get("expiry_date"))
        q = b["quantity"] or 0
        self.qty = line_edit("0", str(q))
        self.rate = line_edit("0.00", f"{((b['amount'] or 0) / q) if q else 0:.2f}")
        self.gst = QComboBox()
        for r in GST_RATES:
            self.gst.addItem(f"{r}%", r)
        rate = b.get("gst_rate") or 0
        if self.gst.findData(rate) < 0:  # non-standard rate saved by an old version
            self.gst.addItem(f"{rate:g}% (as saved)", rate)
        self.gst.setCurrentIndex(self.gst.findData(rate))
        self.tax_type = QComboBox()
        self.tax_type.addItem("Same state (CGST + SGST)", False)
        self.tax_type.addItem("Other state (IGST)", True)
        self.tax_type.setCurrentIndex(1 if (b.get("igst") or 0) > 0 else 0)

        f = self.form
        f.addWidget(Field("Item", self.item), 0, 0, 1, 2)
        f.addWidget(Field("Vendor", self.vendor), 1, 0, 1, 2)
        f.addWidget(Field("Invoice number", self.invoice), 2, 0)
        f.addWidget(Field("Invoice date", self.date), 2, 1)
        f.addWidget(Field("Batch no.", self.batch), 3, 0)
        f.addWidget(Field("Expiry", self.expiry), 3, 1)
        f.addWidget(Field("Quantity", self.qty), 4, 0)
        f.addWidget(Field("Rate / unit, before GST (₹)", self.rate), 4, 1)
        f.addWidget(Field("GST rate", self.gst), 5, 0)
        f.addWidget(Field("Tax type", self.tax_type), 5, 1)
        self.totals = label("")  # explicit two lines: wrapped labels confuse dialog sizing
        self.totals.setProperty("role", "caption")
        self.lay.insertWidget(2, self.totals)
        for w in (self.qty, self.rate):
            w.textChanged.connect(self.recalc)
        for w in (self.gst, self.tax_type):
            w.currentIndexChanged.connect(self.recalc)
        self.recalc()

    def recalc(self):
        try:
            t = line_totals(self.qty.text() or 0, self.rate.text().replace(",", "") or 0,
                            self.gst.currentData() or 0, bool(self.tax_type.currentData()))
        except ValueError:
            self.totals.setText("Enter a valid quantity and rate to see the totals.")
            return
        tax = f"IGST {inr(t['igst'])}" if self.tax_type.currentData() else \
            f"CGST {inr(t['cgst'])} + SGST {inr(t['sgst'])}"
        self.totals.setText(f"Line total: {inr(t['amount'])} + {tax} = {inr(t['total'])}\n"
                            f"The invoice's rupee round-off is recalculated when you save.")

    def save(self):
        item_id, vendor_id = self.item.current_id(), self.vendor.current_id()
        q = self.qty.text().strip()
        if not item_id or not vendor_id:
            self.set_error("Choose an item and a vendor from the lists.")
            return False
        if not q.isdigit() or int(q) <= 0:
            self.set_error("Quantity must be a whole number above 0.")
            return False
        try:
            rate = float(self.rate.text().replace(",", "") or 0)
        except ValueError:
            self.set_error("Enter a valid rate.")
            return False
        try:
            self.bills.update_bill(self.bill_id, item_id, vendor_id, self.invoice.text(), iso(self.date.date()),
                                   self.batch.text(), self.expiry.value(), int(q), rate,
                                   self.gst.currentData() or 0, bool(self.tax_type.currentData()))
        except StockError as e:
            self.set_error(str(e))
            return False
        return True


class ItemLedgerDialog(QDialog):
    """Every movement of one item with a running balance."""

    TYPES = {"PURCHASE": "Purchase", "ISSUE": "Issue", "OPENING": "Opening stock", "ADJUSTMENT": "Correction"}

    def __init__(self, item_id, parent=None):
        super().__init__(parent)
        item = ItemService().get(item_id)
        self.setWindowTitle(f"Item history — {item['name']}")
        self.resize(820, 560)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(22, 18, 22, 16)
        lay.setSpacing(10)
        rows = StockService().item_ledger(item_id)
        balance = rows[-1]["balance"] if rows else 0
        head = QHBoxLayout()
        title = QVBoxLayout()
        title.addWidget(label(item["name"], "pageTitle"))
        title.addWidget(label(f"{len(rows)} movement{'s' if len(rows) != 1 else ''} · "
                              f"current balance {qty(balance)}", "pageSub"))
        head.addLayout(title)
        head.addStretch()
        lay.addLayout(head)
        table = DataTable([("Date", "date"), ("Type", "text"), ("Vendor / issued to", "text"), ("In", "int"),
                           ("Out", "int"), ("Balance", "int")], stretch_col=2, empty_text="No movements yet.")
        table.set_rows([(r["date"], self.TYPES.get(r["txn_type"], r["txn_type"] or ""),
                         r["vendor"].title() if r["txn_type"] == "PURCHASE" else r["remarks"],
                         r["qty_in"] or None, r["qty_out"] or None, r["balance"]) for r in rows])
        lay.addWidget(table, 1)
        row = QHBoxLayout()
        row.addStretch()
        close = button("Close", callback=self.accept)
        close.setDefault(True)
        row.addWidget(close)
        lay.addLayout(row)
        # Newest at the bottom: scroll there
        table.view.scrollToBottom()
