from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QComboBox, QGridLayout, QHBoxLayout, QVBoxLayout

from services.bill_service import BillService
from services.gst import GST_RATES, invoice_totals, line_totals
from services.item_service import ItemService
from services.master_service import MasterError
from services.stock_service import StockError
from services.vendor_service import VendorService
from ui.pages.base import Page
from ui.widgets import (
    Card, DataTable, Field, OptionalDateEdit, SearchCombo, alert, button, confirm, date_edit, divider,
    iso, label, line_edit, toast, uniform_height,
)
from utils.formatting import inr


def gst_combo():
    c = QComboBox()
    for r in GST_RATES:
        c.addItem(f"{r}%", r)
    c.setCurrentIndex(GST_RATES.index(18) if 18 in GST_RATES else 0)
    return c


class PurchasePage(Page):
    nav_key = "purchase"
    title = "New Purchase"
    subtitle = "Enter a vendor invoice — add each item, then save the whole invoice"

    def __init__(self, main):
        super().__init__(main)
        self.bills, self.items, self.vendors = BillService(), ItemService(), VendorService()
        self.lines = []
        self.header.add_action(button("View bills", None, "receipt", callback=lambda: main.navigate("bills")))

        body = QHBoxLayout()
        body.setSpacing(16)

        form = Card(margins=(22, 18, 22, 16), spacing=10)
        form.add(label("INVOICE DETAILS", "section"))
        g = QGridLayout()
        g.setHorizontalSpacing(14)
        g.setVerticalSpacing(8)
        self.vendor = SearchCombo("Type vendor name…")
        self.invoice_no = line_edit("e.g. RT/2026/1184")
        self.invoice_date = date_edit()
        self.tax_type = QComboBox()
        self.tax_type.addItem("Same state (CGST + SGST)", False)
        self.tax_type.addItem("Other state (IGST)", True)
        self.f_vendor = Field("Vendor", self.vendor)
        self.f_invoice = Field("Invoice number", self.invoice_no)
        g.addWidget(self.f_vendor, 0, 0, 1, 2)
        g.addWidget(self.f_invoice, 0, 2)
        g.addWidget(Field("Invoice date", self.invoice_date), 0, 3)
        g.addWidget(Field("Tax type", self.tax_type), 0, 4)
        for col in range(5):
            g.setColumnStretch(col, 1)
        form.add(g)

        form.add(label("ADD ITEM", "section"))
        g = QGridLayout()
        g.setHorizontalSpacing(14)
        g.setVerticalSpacing(8)
        self.item = SearchCombo("Type item name…")
        self.batch = line_edit("Optional")
        self.expiry = OptionalDateEdit()
        self.qty = line_edit("0")
        self.rate = line_edit("0.00")
        self.gst = gst_combo()
        self.f_item = Field("Item", self.item)
        self.f_qty = Field("Quantity", self.qty)
        self.f_rate = Field("Rate / unit, before GST (₹)", self.rate)
        g.addWidget(self.f_item, 0, 0, 1, 2)
        g.addWidget(Field("Batch no.", self.batch), 0, 2)
        g.addWidget(Field("Expiry", self.expiry), 0, 3)
        g.addWidget(self.f_qty, 1, 0)
        g.addWidget(self.f_rate, 1, 1)
        g.addWidget(Field("GST rate", self.gst), 1, 2)
        self.add_btn = button("Add to invoice", None, "plus", "Add this item (Enter)", self.add_line)
        uniform_height(self.add_btn)
        add_wrap = QVBoxLayout()
        add_wrap.addStretch()
        add_wrap.addWidget(self.add_btn)
        g.addLayout(add_wrap, 1, 3, Qt.AlignmentFlag.AlignBottom)
        for col in range(5):
            g.setColumnStretch(col, 1)
        form.add(g)

        head = QHBoxLayout()
        head.addWidget(label("ITEMS ON THIS INVOICE", "section"))
        head.addStretch()
        self.remove_btn = button("Remove", "danger", "trash", "Remove the selected line (Delete)", self.remove_line)
        self.remove_btn.setVisible(False)
        head.addWidget(self.remove_btn)
        form.add(head)
        self.table = DataTable([("Item", "text"), ("Batch", "text"), ("Expiry", "date"), ("Qty", "int"),
                                ("Rate", "money"), ("GST", "pct"), ("Amount", "money")],
                               empty_text="No items yet — add the first item above.")
        self.table.selection_changed.connect(lambda: self.remove_btn.setVisible(self.table.selected_id() is not None))
        self.table.activated.connect(self.edit_line)
        form.add(self.table, 1)
        body.addWidget(form, 1)

        summary = Card(margins=(20, 18, 20, 18), spacing=10)
        summary.setFixedWidth(300)
        summary.add(label("Invoice summary", "cardTitle"))
        self.sum_labels = {}
        for key, text in [("items", "Items"), ("amount", "Taxable value"), ("cgst", "CGST"),
                          ("sgst", "SGST"), ("igst", "IGST"), ("round_off", "Round off")]:
            row = QHBoxLayout()
            name = label(text, "caption")
            val = label("—")
            val.setAlignment(Qt.AlignmentFlag.AlignRight)
            row.addWidget(name)
            row.addStretch()
            row.addWidget(val)
            summary.add(row)
            self.sum_labels[key] = (name, val)
        summary.add(divider())
        net_row = QHBoxLayout()
        net_row.addWidget(label("Net amount", "cardTitle"))
        net_row.addStretch()
        self.net = label("₹0", "bigNumber")
        net_row.addWidget(self.net)
        summary.add(net_row)
        summary.layout_.addStretch()
        self.save_btn = button("Save purchase", "primary", "floppy-disk", "Save the invoice (Ctrl+S)", self.on_save)
        summary.add(self.save_btn)
        hint = label("Ctrl + S to save  ·  Esc to clear", "caption")
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        summary.add(hint)
        summary.add(button("Clear form", None, None, None, self.on_escape))
        body.addWidget(summary)
        self.root.addLayout(body, 1)

        # Keyboard flow: Enter moves forward / adds the line
        self.vendor.lineEdit().returnPressed.connect(self.invoice_no.setFocus)
        self.invoice_no.returnPressed.connect(self.item.setFocus)
        self.item.lineEdit().returnPressed.connect(self.batch.setFocus)
        self.batch.returnPressed.connect(self.qty.setFocus)
        self.qty.returnPressed.connect(self.rate.setFocus)
        self.rate.returnPressed.connect(self.add_line)
        self.tax_type.currentIndexChanged.connect(self.update_summary)
        self.update_summary()

    # ---- data -----------------------------------------------------------------------

    def refresh(self):
        self.vendor.set_items([(v["id"], v["name"]) for v in self.vendors.get_all()])
        self.item.set_items([(i["id"], i["name"]) for i in self.items.get_all()])

    def _resolve(self, combo, field, service, noun):
        """Selected id, offering to add a typed name that isn't in the list yet."""
        row_id = combo.current_id()
        text = combo.currentText().strip()
        if row_id:
            field.set_error()
            return row_id
        if not text:
            field.set_error(f"Choose a {noun}.")
            return None
        if not confirm(self, f"New {noun}?", f"'{text}' is not in the {noun} list.\n\nAdd it as a new {noun}?",
                       ok_text=f"Add {noun}", danger=False):
            field.set_error(f"Choose a {noun} from the list.")
            return None
        try:
            new_id = service.add(text)
        except MasterError as e:
            field.set_error(str(e))
            return None
        self.refresh()
        combo.set_current_id(new_id)
        field.set_error()
        toast(self, f"{noun.title()} '{text}' added")
        return new_id

    # ---- lines --------------------------------------------------------------------

    def _line_has_input(self):
        return bool(self.item.currentText().strip() or self.qty.text().strip() or self.rate.text().strip())

    def add_line(self):
        item_id = self._resolve(self.item, self.f_item, self.items, "item")
        q, r = self.qty.text().strip(), self.rate.text().strip().replace(",", "")
        ok = item_id is not None
        if not q.isdigit() or int(q) <= 0:
            self.f_qty.set_error("Enter a whole number above 0.")
            ok = False
        else:
            self.f_qty.set_error()
        try:
            rate = float(r or 0)
            if rate < 0:
                raise ValueError
            self.f_rate.set_error()
        except ValueError:
            self.f_rate.set_error("Enter a valid rate.")
            ok = False
        if not ok:
            return False
        self.lines.append({
            "item_id": item_id, "item_name": self.item.currentText().strip(), "batch_number": self.batch.text().strip(),
            "expiry_date": self.expiry.value(), "quantity": int(q), "rate": rate, "gst_rate": self.gst.currentData(),
        })
        self.item.reset()
        self.batch.clear()
        self.expiry.set_value(None)
        self.qty.clear()
        self.rate.clear()
        self.item.setFocus()
        self.update_lines()
        return True

    def edit_line(self, index):
        """Double-click a line: put it back into the fields to correct it."""
        ln = self.lines.pop(index)
        self.item.set_current_id(ln["item_id"])
        self.batch.setText(ln["batch_number"])
        self.expiry.set_value(ln["expiry_date"])
        self.qty.setText(str(ln["quantity"]))
        self.rate.setText(f"{ln['rate']:g}")
        self.gst.setCurrentIndex(self.gst.findData(ln["gst_rate"]))
        self.update_lines()
        self.qty.setFocus()

    def remove_line(self):
        idx = self.table.selected_id()
        if idx is not None:
            self.lines.pop(idx)
            self.update_lines()

    def update_lines(self):
        interstate = bool(self.tax_type.currentData())
        rows = []
        for ln in self.lines:
            t = line_totals(ln["quantity"], ln["rate"], ln["gst_rate"], interstate)
            rows.append((ln["item_name"], ln["batch_number"], ln["expiry_date"], ln["quantity"],
                         ln["rate"], ln["gst_rate"], float(t["amount"])))
        self.table.set_rows(rows, ids=list(range(len(rows))))
        self.update_summary()

    def update_summary(self):
        interstate = bool(self.tax_type.currentData())
        t = invoice_totals(self.lines, interstate)
        for key, (name, val) in self.sum_labels.items():
            if key == "items":
                val.setText(str(t["items"]))
                continue
            visible = not ((key == "igst" and not interstate) or (key in ("cgst", "sgst") and interstate))
            name.setVisible(visible)
            val.setVisible(visible)
            val.setText(inr(t[key]))
        self.net.setText(inr(t["net_amount"], 0 if t["net_amount"] == int(t["net_amount"]) else 2))

    # ---- save / clear ---------------------------------------------------------------

    def on_save(self):
        # An item typed but not yet added is added first
        if self._line_has_input() and not self.add_line():
            return
        vendor_id = self._resolve(self.vendor, self.f_vendor, self.vendors, "vendor")
        number = self.invoice_no.text().strip()
        self.f_invoice.set_error("" if number else "Enter the invoice number.")
        if not vendor_id or not number:
            return
        if not self.lines:
            alert(self, "No items", "Add at least one item to the invoice.")
            return
        if self.bills.invoice_exists(vendor_id, number) and not confirm(
                self, "Invoice already entered",
                f"Invoice '{number}' from {self.vendor.currentText()} is already saved.\n\n"
                "Save these items under the same invoice anyway?", ok_text="Save anyway", danger=False):
            return
        try:
            self.bills.add_invoice(vendor_id, number, iso(self.invoice_date.date()), self.lines,
                                   bool(self.tax_type.currentData()))
        except StockError as e:
            alert(self, "Cannot save", str(e))
            return
        t = invoice_totals(self.lines, bool(self.tax_type.currentData()))
        toast(self, f"Invoice {number} saved · {t['items']} item{'s' if t['items'] != 1 else ''} · "
                    f"{inr(t['net_amount'])}")
        self._reset(keep_date=True)

    def on_escape(self):
        if (self.lines or self._line_has_input()) and not confirm(
                self, "Clear this invoice?", "The items you've added will be removed.", ok_text="Clear"):
            return
        self._reset(keep_date=True)

    def _reset(self, keep_date):
        self.lines = []
        self.vendor.reset()
        self.invoice_no.clear()
        self.item.reset()
        self.batch.clear()
        self.expiry.set_value(None)
        self.qty.clear()
        self.rate.clear()
        for f in (self.f_vendor, self.f_invoice, self.f_item, self.f_qty, self.f_rate):
            f.set_error()
        if not keep_date:
            self.invoice_date.setDate(self.invoice_date.maximumDate())
        self.update_lines()
        self.vendor.setFocus()

    def keyPressEvent(self, e):
        if e.key() == Qt.Key.Key_Delete and self.table.view.hasFocus():
            self.remove_line()
            return
        super().keyPressEvent(e)
