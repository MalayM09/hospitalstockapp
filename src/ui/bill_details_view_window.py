from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTableWidget,
    QTableWidgetItem, QHeaderView, QFileDialog, QMessageBox, QFrame,
    QDialog, QLineEdit, QComboBox, QDateEdit, QGridLayout
)
from PyQt6.QtCore import Qt, QDate
from PyQt6.QtPrintSupport import QPrinter, QPrintDialog
from PyQt6.QtGui import QTextDocument
import pandas as pd
from datetime import datetime

from services.bill_service import BillService
from services.gst import GST_RATES, compute_totals
from services.stock_service import StockError
from services.vendor_service import VendorService
from services.item_service import ItemService


class BillDetailsViewWindow(QWidget):
    """Window to display all bill details with edit/delete functionality."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Bill Details View")
        self.setMinimumSize(1200, 800)
        self.setStyleSheet("background-color: #F5F7FA;")

        self.bill_service = BillService()
        self.vendor_service = VendorService()
        self.item_service = ItemService()
        self.last_data = None

        self.init_ui()
        self.load_data()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Header
        header = self.create_header("📄", "Bill Details", "View, edit, and delete purchase records")
        main_layout.addWidget(header)

        # Content
        content = QWidget()
        content.setStyleSheet("background-color: #F5F7FA;")
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(40, 40, 40, 40)
        content_layout.setSpacing(20)

        # Table Card
        table_card = self.create_card()
        table_layout = QVBoxLayout(table_card)
        table_layout.setContentsMargins(20, 20, 20, 20)

        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(13)
        self.table.setHorizontalHeaderLabels([
            "ID", "Invoice Date", "Vendor", "Item Name", "Invoice No.", "Batch No.",
            "Expiry Date", "Qty.", "Amount", "GST %", "Tax", "Round Off", "Net Amount"
        ])
        self.table.setStyleSheet("""
            QTableWidget {
                background-color: white;
                border: none;
                gridline-color: #E0E6ED;
                font-size: 13px;
            }
            QTableWidget::item {
                padding: 12px;
                border-bottom: 1px solid #E0E6ED;
            }
            QTableWidget::item:selected {
                background-color: #FFF3E0;
                color: #E65100;
            }
            QHeaderView::section {
                background-color: #E65100;
                color: white;
                padding: 14px;
                font-weight: bold;
                font-size: 13px;
                border: none;
            }
        """)

        header_view = self.table.horizontalHeader()
        header_view.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        header_view.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)

        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.setStyleSheet(self.table.styleSheet() + """
            QTableWidget {
                alternate-background-color: #FAFAFA;
            }
        """)

        table_layout.addWidget(self.table)
        content_layout.addWidget(table_card)

        # Button row
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(15)

        refresh_btn = self.create_button("🔄 Refresh", "#E65100", self.load_data)
        edit_btn = self.create_button("✏️ Edit Selected", "#1565C0", self.edit_selected)
        delete_btn = self.create_button("🗑️ Delete Selected", "#C62828", self.delete_selected)
        export_btn = self.create_button("📊 Export", "#00695C", self.export_to_excel)
        print_btn = self.create_button("🖨️ Print", "#7B1FA2", self.print_report)
        close_btn = self.create_button("← Back", "#546E7A", self.close)

        btn_layout.addWidget(refresh_btn)
        btn_layout.addWidget(edit_btn)
        btn_layout.addWidget(delete_btn)
        btn_layout.addWidget(export_btn)
        btn_layout.addWidget(print_btn)
        btn_layout.addStretch()
        btn_layout.addWidget(close_btn)

        content_layout.addLayout(btn_layout)
        main_layout.addWidget(content)

    def create_header(self, icon, title, subtitle):
        header = QFrame()
        header.setFixedHeight(100)
        header.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #BF360C, stop:1 #E65100);
            }
        """)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(40, 0, 40, 0)

        icon_label = QLabel(icon)
        icon_label.setStyleSheet("font-size: 40px; background: transparent;")
        header_layout.addWidget(icon_label)

        title_layout = QVBoxLayout()
        title_label = QLabel(title)
        title_label.setStyleSheet("font-size: 28px; font-weight: bold; color: white; background: transparent;")
        subtitle_label = QLabel(subtitle)
        subtitle_label.setStyleSheet("font-size: 14px; color: rgba(255,255,255,0.8); background: transparent;")
        title_layout.addWidget(title_label)
        title_layout.addWidget(subtitle_label)
        header_layout.addLayout(title_layout)

        header_layout.addStretch()

        return header

    def create_card(self):
        card = QFrame()
        card.setStyleSheet("QFrame { background-color: white; border-radius: 16px; }")
        return card

    def create_button(self, text, color, callback):
        btn = QPushButton(text)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {color};
                color: white;
                border: none;
                border-radius: 10px;
                padding: 12px 20px;
                font-size: 13px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background-color: {color}DD;
            }}
        """)
        btn.clicked.connect(callback)
        return btn

    def load_data(self):
        records = self.bill_service.get_bill_details_view()
        self.table.clearSpans()  # a previous "No data found" row may have merged cells
        self.table.setRowCount(len(records))

        data_for_export = []
        for row_idx, record in enumerate(records):
            values = [
                str(record['sr_no']),
                str(record['date'] or '-'),
                record['vendor'],
                str(record['item_name'] or '-'),
                str(record['invoice_no'] or '-'),
                str(record['batch_no'] or '-'),
                str(record['expiry_date'] or '-'),
                str(record['qty'] or 0),
                f"₹{record['amount'] or 0:.2f}",
                f"{record['gst_rate']:g}%",
                f"₹{record['tax'] or 0:.2f}",
                f"₹{record['round_off'] or 0:.2f}",
                f"₹{record['net_amount'] or 0:.2f}",
            ]
            for col, value in enumerate(values):
                self.table.setItem(row_idx, col, QTableWidgetItem(value))
            self.table.item(row_idx, 12).setForeground(Qt.GlobalColor.darkGreen)

            data_for_export.append({
                'ID': record['sr_no'],
                'Invoice Date': record['date'],
                'Vendor': record['vendor'],
                'Item Name': record['item_name'],
                'Invoice No.': record['invoice_no'],
                'Batch No.': record['batch_no'],
                'Expiry Date': record['expiry_date'],
                'Qty.': record['qty'],
                'Amount': record['amount'],
                'GST %': record['gst_rate'],
                'Tax': record['tax'],
                'Round Off': record['round_off'],
                'Net Amount': record['net_amount']
            })

        self.last_data = data_for_export

        if not records:
            self.table.setRowCount(1)
            self.table.setItem(0, 0, QTableWidgetItem("No data found"))
            self.table.setSpan(0, 0, 1, self.table.columnCount())

    def get_selected_bill_id(self):
        """Get the ID of the selected bill."""
        selected = self.table.currentRow()
        if selected < 0:
            return None
        id_item = self.table.item(selected, 0)
        if id_item and id_item.text().isdigit():
            return int(id_item.text())
        return None

    def edit_selected(self):
        """Open edit dialog for selected bill."""
        bill_id = self.get_selected_bill_id()
        if bill_id is None:
            QMessageBox.warning(self, "Error", "Please select a bill to edit")
            return

        # Get bill details
        bill = self.bill_service.get_bill_by_id(bill_id)
        if not bill:
            QMessageBox.warning(self, "Error", "Bill not found")
            return

        dialog = EditBillDialog(bill, self.vendor_service, self.item_service, self)
        while dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_data()
            if data is None:
                continue  # validation message already shown; keep the dialog open
            try:
                self.bill_service.update_bill(bill_id=bill_id, **data)
            except StockError as e:
                QMessageBox.warning(self, "Cannot Save", str(e))
                continue
            QMessageBox.information(self, "Success", "Bill updated successfully!")
            self.load_data()
            break

    def delete_selected(self):
        """Delete selected bill with confirmation."""
        bill_id = self.get_selected_bill_id()
        if bill_id is None:
            QMessageBox.warning(self, "Error", "Please select a bill to delete")
            return

        reply = QMessageBox.question(
            self, "Confirm Delete",
            f"Are you sure you want to delete Bill #{bill_id}?\n\n"
            "The stock it added will be removed too.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            try:
                self.bill_service.delete_bill(bill_id)
            except StockError as e:
                QMessageBox.warning(self, "Cannot Delete", str(e))
                return
            QMessageBox.information(self, "Success", "Bill deleted successfully!")
            self.load_data()

    def export_to_excel(self):
        if not self.last_data:
            QMessageBox.warning(self, "Error", "No data to export")
            return

        path, _ = QFileDialog.getSaveFileName(
            self, "Save Bill Details", "", "Excel Files (*.xlsx)"
        )

        if path:
            df = pd.DataFrame(self.last_data)
            df.to_excel(path, index=False)
            QMessageBox.information(self, "Success", "Bill details exported successfully!")

    def print_report(self):
        """Print bill details."""
        if not self.last_data:
            QMessageBox.warning(self, "Error", "No data to print")
            return

        printer = QPrinter(QPrinter.PrinterMode.HighResolution)
        dialog = QPrintDialog(printer, self)

        if dialog.exec() == QPrintDialog.DialogCode.Accepted:
            html = f"""
            <html>
            <head>
                <style>
                    body {{ font-family: Arial, sans-serif; }}
                    h1 {{ text-align: center; color: #E65100; }}
                    table {{ width: 100%; border-collapse: collapse; margin-top: 20px; font-size: 11px; }}
                    th {{ background-color: #E65100; color: white; padding: 8px; text-align: left; }}
                    td {{ padding: 6px; border-bottom: 1px solid #ddd; }}
                    tr:nth-child(even) {{ background-color: #f2f2f2; }}
                    .date {{ font-size: 12px; color: #666; text-align: center; }}
                </style>
            </head>
            <body>
                <h1>Bill Details Report</h1>
                <p class="date">Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}</p>
                <table>
                    <tr>
                        <th>ID</th><th>Date</th><th>Vendor</th><th>Invoice</th>
                        <th>Qty</th><th>Amount</th><th>Tax</th><th>Net</th>
                    </tr>
            """

            for item in self.last_data:
                html += f"""
                    <tr>
                        <td>{item['ID']}</td>
                        <td>{item['Invoice Date']}</td>
                        <td>{item['Vendor']}</td>
                        <td>{item['Invoice No.']}</td>
                        <td>{item['Qty.']}</td>
                        <td>₹{item['Amount']}</td>
                        <td>₹{item['Tax']}</td>
                        <td>₹{item['Net Amount']}</td>
                    </tr>
                """

            html += "</table></body></html>"

            doc = QTextDocument()
            doc.setHtml(html)
            doc.print_(printer)
            QMessageBox.information(self, "Success", "Print job sent!")


class EditBillDialog(QDialog):
    """
    Edit every field of a bill. Taxes and the net amount are recalculated live
    from quantity x rate and the GST rate, exactly as in Purchase Entry.
    """

    def __init__(self, bill, vendor_service, item_service, parent=None):
        super().__init__(parent)
        self.bill = bill
        self.vendor_service = vendor_service
        self.item_service = item_service
        self.setWindowTitle(f"Edit Bill #{bill['id']}")
        self.setMinimumWidth(560)
        self.setStyleSheet("background-color: white;")
        self.init_ui()
        self.recalculate()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(30, 30, 30, 30)

        title = QLabel(f"Edit Bill #{self.bill['id']}")
        title.setStyleSheet("font-size: 20px; font-weight: bold; color: #E65100;")
        layout.addWidget(title)

        grid = QGridLayout()
        grid.setSpacing(10)
        row = 0

        def add_row(label, widget):
            nonlocal row
            grid.addWidget(self.create_label(label), row, 0)
            grid.addWidget(widget, row, 1)
            row += 1

        self.item_combo = QComboBox()
        for i in self.item_service.get_all_items():
            self.item_combo.addItem(i['name'], i['id'])
        self.item_combo.setCurrentIndex(max(0, self.item_combo.findData(self.bill['item_id'])))
        add_row("Item", self.item_combo)

        self.vendor_combo = QComboBox()
        for v in self.vendor_service.get_all_vendors():
            self.vendor_combo.addItem(v['name'], v['id'])
        self.vendor_combo.setCurrentIndex(max(0, self.vendor_combo.findData(self.bill['vendor_id'])))
        add_row("Vendor", self.vendor_combo)

        self.invoice_input = QLineEdit(self.bill['invoice_number'] or '')
        add_row("Invoice No.", self.invoice_input)

        self.date_input = QDateEdit()
        self.date_input.setDisplayFormat("dd-MM-yyyy")
        self.date_input.setCalendarPopup(True)
        self.date_input.setMaximumDate(QDate.currentDate())
        inv_date = self.bill['invoice_date'] or self.bill['entry_date']
        self.date_input.setDate(QDate.fromString(inv_date, "yyyy-MM-dd") if inv_date else QDate.currentDate())
        add_row("Invoice Date", self.date_input)

        self.batch_input = QLineEdit(self.bill['batch_number'] or '')
        add_row("Batch No.", self.batch_input)

        self.expiry_input = QDateEdit()
        self.expiry_input.setDisplayFormat("dd-MM-yyyy")
        self.expiry_input.setCalendarPopup(True)
        if self.bill.get('expiry_date'):
            self.expiry_input.setDate(QDate.fromString(self.bill['expiry_date'], "yyyy-MM-dd"))
        else:
            self.expiry_input.setDate(QDate.currentDate().addYears(1))
        add_row("Expiry Date", self.expiry_input)

        qty = self.bill['quantity'] or 0
        self.qty_input = QLineEdit(str(qty))
        self.qty_input.textChanged.connect(self.recalculate)
        add_row("Quantity", self.qty_input)

        rate = (self.bill['amount'] or 0) / qty if qty else (self.bill['amount'] or 0)
        self.rate_input = QLineEdit(f"{rate:.2f}")
        self.rate_input.textChanged.connect(self.recalculate)
        add_row("Rate per Unit, before GST (₹)", self.rate_input)

        self.gst_combo = QComboBox()
        for r in GST_RATES:
            self.gst_combo.addItem(f"{r}%", r)
        current_rate = self.bill.get('gst_rate') or 0
        idx = self.gst_combo.findData(current_rate)
        if idx < 0:
            # Bill saved with a non-standard rate (e.g. by the old CGST/SGST dropdowns)
            self.gst_combo.addItem(f"{current_rate:g}% (as saved)", current_rate)
            idx = self.gst_combo.count() - 1
        self.gst_combo.setCurrentIndex(idx)
        self.gst_combo.currentIndexChanged.connect(self.recalculate)
        add_row("GST Rate (total)", self.gst_combo)

        self.type_combo = QComboBox()
        self.type_combo.addItem("Same state (CGST + SGST)", False)
        self.type_combo.addItem("Other state (IGST)", True)
        self.type_combo.setCurrentIndex(1 if (self.bill.get('igst') or 0) > 0 else 0)
        self.type_combo.currentIndexChanged.connect(self.recalculate)
        add_row("Tax Type", self.type_combo)

        layout.addLayout(grid)

        self.totals_label = QLabel()
        self.totals_label.setStyleSheet("""
            background-color: #E8F5E9; border: 2px solid #4CAF50; border-radius: 10px;
            padding: 12px; font-size: 14px; color: #1B5E20;
        """)
        layout.addWidget(self.totals_label)

        btn_layout = QHBoxLayout()
        save_btn = QPushButton("💾 Save")
        save_btn.setStyleSheet("""
            QPushButton { background-color: #E65100; color: white; border: none; border-radius: 8px;
                          padding: 12px 30px; font-weight: bold; }
            QPushButton:hover { background-color: #BF360C; }
        """)
        save_btn.clicked.connect(self.accept)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setStyleSheet("""
            QPushButton { background-color: #9E9E9E; color: white; border: none; border-radius: 8px;
                          padding: 12px 30px; }
            QPushButton:hover { background-color: #757575; }
        """)
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(save_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)

    def create_label(self, text):
        label = QLabel(text)
        label.setStyleSheet("font-size: 13px; font-weight: 600; color: #333;")
        return label

    def recalculate(self):
        try:
            t = compute_totals(self.qty_input.text().strip() or 0, self.rate_input.text().strip() or 0,
                               self.gst_combo.currentData() or 0, bool(self.type_combo.currentData()))
        except ValueError:
            self.totals_label.setText("Enter a valid quantity and rate to see the totals.")
            return
        tax = (f"IGST ₹{t['igst']:.2f}" if self.type_combo.currentData()
               else f"CGST ₹{t['cgst']:.2f} + SGST ₹{t['sgst']:.2f}")
        self.totals_label.setText(
            f"Amount ₹{t['amount']:.2f}   +   {tax}   +   Round off ₹{t['round_off']:.2f}\n"
            f"Net Amount:  ₹{t['net_amount']:.2f}"
        )

    def get_data(self):
        """Validated values for BillService.update_bill, or None (after showing why)."""
        qty_text = self.qty_input.text().strip()
        if not qty_text.isdigit() or int(qty_text) <= 0:
            QMessageBox.warning(self, "Error", "Quantity must be a whole number greater than zero.")
            return None
        try:
            rate = float(self.rate_input.text().strip() or 0)
        except ValueError:
            QMessageBox.warning(self, "Error", "Rate must be a number (e.g. 125.50).")
            return None
        if rate < 0:
            QMessageBox.warning(self, "Error", "Rate cannot be negative.")
            return None
        if not self.invoice_input.text().strip():
            QMessageBox.warning(self, "Error", "Please enter an invoice number.")
            return None
        return {
            'item_id': self.item_combo.currentData(),
            'vendor_id': self.vendor_combo.currentData(),
            'invoice_number': self.invoice_input.text().strip(),
            'invoice_date': self.date_input.date().toString("yyyy-MM-dd"),
            'batch_number': self.batch_input.text().strip(),
            'expiry_date': self.expiry_input.date().toString("yyyy-MM-dd"),
            'quantity': int(qty_text),
            'rate': rate,
            'gst_rate': self.gst_combo.currentData() or 0,
            'interstate': bool(self.type_combo.currentData()),
        }
