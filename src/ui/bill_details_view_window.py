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
        self.table.setColumnCount(10)
        self.table.setHorizontalHeaderLabels([
            "ID", "Date", "Vendor", "Invoice No.", "Batch No.",
            "Qty.", "Amount", "Tax", "Round Off", "Net Amount"
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
        self.table.setRowCount(len(records))

        data_for_export = []

        for row_idx, record in enumerate(records):
            self.table.setItem(row_idx, 0, QTableWidgetItem(str(record['sr_no'])))
            self.table.setItem(row_idx, 1, QTableWidgetItem(str(record['date'] or '-')))
            self.table.setItem(row_idx, 2, QTableWidgetItem(record['vendor']))
            self.table.setItem(row_idx, 3, QTableWidgetItem(str(record['invoice_no'] or '-')))
            self.table.setItem(row_idx, 4, QTableWidgetItem(str(record['batch_no'] or '-')))
            self.table.setItem(row_idx, 5, QTableWidgetItem(str(record['qty'] or 0)))
            self.table.setItem(row_idx, 6, QTableWidgetItem(f"₹{record['amount'] or 0}"))
            self.table.setItem(row_idx, 7, QTableWidgetItem(f"₹{record['tax'] or 0}"))
            self.table.setItem(row_idx, 8, QTableWidgetItem(f"₹{record['round_off'] or 0}"))

            net_item = QTableWidgetItem(f"₹{record['net_amount'] or 0}")
            net_item.setForeground(Qt.GlobalColor.darkGreen)
            self.table.setItem(row_idx, 9, net_item)

            data_for_export.append({
                'ID': record['sr_no'],
                'Date': record['date'],
                'Vendor': record['vendor'],
                'Invoice No.': record['invoice_no'],
                'Batch No.': record['batch_no'],
                'Qty.': record['qty'],
                'Amount': record['amount'],
                'Tax': record['tax'],
                'Round Off': record['round_off'],
                'Net Amount': record['net_amount']
            })

        self.last_data = data_for_export

        if not records:
            self.table.setRowCount(1)
            self.table.setItem(0, 0, QTableWidgetItem("No data found"))
            self.table.setSpan(0, 0, 1, 10)

    def get_selected_bill_id(self):
        """Get the ID of the selected bill."""
        selected = self.table.currentRow()
        if selected < 0:
            return None
        id_item = self.table.item(selected, 0)
        if id_item:
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

        # Create edit dialog
        dialog = EditBillDialog(bill, self.vendor_service, self.item_service, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_data()
            self.bill_service.update_bill(
                bill_id=bill_id,
                item_id=data['item_id'],
                vendor_id=data['vendor_id'],
                invoice_number=data['invoice_number'],
                invoice_date=data['invoice_date'],
                batch_number=data['batch_number'],
                quantity=data['quantity'],
                amount=data['amount'],
                cgst=data['cgst'],
                sgst=data['sgst'],
                round_off=data['round_off'],
                net_amount=data['net_amount']
            )
            QMessageBox.information(self, "Success", "Bill updated successfully!")
            self.load_data()

    def delete_selected(self):
        """Delete selected bill with confirmation."""
        bill_id = self.get_selected_bill_id()
        if bill_id is None:
            QMessageBox.warning(self, "Error", "Please select a bill to delete")
            return

        reply = QMessageBox.question(
            self, "Confirm Delete",
            f"Are you sure you want to delete Bill #{bill_id}?\n\nThis action cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.bill_service.delete_bill(bill_id)
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
                        <td>{item['Date']}</td>
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
    """Dialog for editing a bill."""

    def __init__(self, bill, vendor_service, item_service, parent=None):
        super().__init__(parent)
        self.bill = bill
        self.vendor_service = vendor_service
        self.item_service = item_service
        self.setWindowTitle("Edit Bill")
        self.setFixedSize(500, 500)
        self.setStyleSheet("background-color: white;")
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(30, 30, 30, 30)

        title = QLabel("Edit Bill Details")
        title.setStyleSheet("font-size: 20px; font-weight: bold; color: #E65100;")
        layout.addWidget(title)

        # Grid for form
        grid = QGridLayout()
        grid.setSpacing(10)

        # Vendor
        grid.addWidget(self.create_label("Vendor"), 0, 0)
        self.vendor_combo = QComboBox()
        for v in self.vendor_service.get_all_vendors():
            vendor_id = v[0] if isinstance(v, (tuple, list)) else v['id']
            vendor_name = v[1] if isinstance(v, (tuple, list)) else v['name']
            self.vendor_combo.addItem(vendor_name, vendor_id)
        self.vendor_combo.setCurrentIndex(self.vendor_combo.findData(self.bill['vendor_id']))
        grid.addWidget(self.vendor_combo, 0, 1)

        # Invoice Number
        grid.addWidget(self.create_label("Invoice No."), 1, 0)
        self.invoice_input = QLineEdit(self.bill['invoice_number'] or '')
        grid.addWidget(self.invoice_input, 1, 1)

        # Invoice Date
        grid.addWidget(self.create_label("Invoice Date"), 2, 0)
        self.date_input = QDateEdit()
        if self.bill['invoice_date']:
            self.date_input.setDate(QDate.fromString(self.bill['invoice_date'], "yyyy-MM-dd"))
        self.date_input.setCalendarPopup(True)
        grid.addWidget(self.date_input, 2, 1)

        # Batch Number
        grid.addWidget(self.create_label("Batch No."), 3, 0)
        self.batch_input = QLineEdit(self.bill['batch_number'] or '')
        grid.addWidget(self.batch_input, 3, 1)

        # Quantity
        grid.addWidget(self.create_label("Quantity"), 4, 0)
        self.qty_input = QLineEdit(str(self.bill['quantity'] or 0))
        grid.addWidget(self.qty_input, 4, 1)

        # Amount
        grid.addWidget(self.create_label("Amount"), 5, 0)
        self.amount_input = QLineEdit(str(self.bill['amount'] or 0))
        grid.addWidget(self.amount_input, 5, 1)

        layout.addLayout(grid)

        # Buttons
        btn_layout = QHBoxLayout()
        
        save_btn = QPushButton("💾 Save")
        save_btn.setStyleSheet("""
            QPushButton {
                background-color: #E65100;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 12px 30px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #BF360C; }
        """)
        save_btn.clicked.connect(self.accept)
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #9E9E9E;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 12px 30px;
            }
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

    def get_data(self):
        qty = int(self.qty_input.text() or 0)
        amount = float(self.amount_input.text() or 0)
        # Recalculate net amount (simplified - assumes same tax rate)
        net_amount = amount  # You may want to add tax recalculation here
        
        return {
            'item_id': self.bill['item_id'],
            'vendor_id': self.vendor_combo.currentData(),
            'invoice_number': self.invoice_input.text(),
            'invoice_date': self.date_input.date().toString("yyyy-MM-dd"),
            'batch_number': self.batch_input.text(),
            'quantity': qty,
            'amount': amount,
            'cgst': self.bill['cgst'] or 0,
            'sgst': self.bill['sgst'] or 0,
            'round_off': self.bill['round_off'] or 0,
            'net_amount': self.bill['net_amount'] or amount
        }
