from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QComboBox,
    QPushButton, QMessageBox, QListWidget, QDateEdit, QFrame, QScrollArea, QGridLayout
)
from PyQt6.QtCore import Qt, QDate
from decimal import Decimal, ROUND_HALF_UP

from services.db_service import get_db
from services.bill_service import BillService
from services.vendor_service import VendorService
from services.item_service import ItemService


class BillEntryWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Purchase Entry")
        self.setMinimumSize(1200, 800)
        self.setStyleSheet("background-color: #F5F7FA;")

        self.db = get_db()
        self.bill_service = BillService()
        self.vendor_service = VendorService()
        self.item_service = ItemService()

        self.init_ui()
        self.load_vendors()
        self.load_items()
        self.load_recent_bills()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Header
        header = self.create_header("🛒", "Purchase Entry", "Record new purchases from vendors")
        main_layout.addWidget(header)

        # Content with scroll
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background-color: #F5F7FA; }")

        content = QWidget()
        content.setStyleSheet("background-color: #F5F7FA;")
        content_layout = QHBoxLayout(content)
        content_layout.setContentsMargins(40, 40, 40, 40)
        content_layout.setSpacing(30)

        # Left Panel - Form
        form_card = self.create_card()
        form_layout = QVBoxLayout(form_card)
        form_layout.setContentsMargins(30, 30, 30, 30)
        form_layout.setSpacing(15)

        form_title = QLabel("New Purchase Entry")
        form_title.setStyleSheet("font-size: 20px; font-weight: bold; color: #1A1A2E; background: transparent;")
        form_layout.addWidget(form_title)

        # Item and Vendor row
        row1 = QHBoxLayout()
        item_layout = QVBoxLayout()
        item_layout.addWidget(self.create_label("Item"))
        self.item_dropdown = QComboBox()
        self.style_combo(self.item_dropdown)
        item_layout.addWidget(self.item_dropdown)
        row1.addLayout(item_layout)

        vendor_layout = QVBoxLayout()
        vendor_layout.addWidget(self.create_label("Vendor"))
        self.vendor_dropdown = QComboBox()
        self.style_combo(self.vendor_dropdown)
        vendor_layout.addWidget(self.vendor_dropdown)
        row1.addLayout(vendor_layout)
        form_layout.addLayout(row1)

        # Invoice details row
        row2 = QHBoxLayout()
        inv_num_layout = QVBoxLayout()
        inv_num_layout.addWidget(self.create_label("Invoice Number"))
        self.invoice_number_input = self.create_input("INV-001")
        inv_num_layout.addWidget(self.invoice_number_input)
        row2.addLayout(inv_num_layout)

        inv_date_layout = QVBoxLayout()
        inv_date_layout.addWidget(self.create_label("Invoice Date"))
        self.invoice_date_input = QDateEdit()
        self.invoice_date_input.setDate(QDate.currentDate())
        self.invoice_date_input.setCalendarPopup(True)
        self.style_date(self.invoice_date_input)
        inv_date_layout.addWidget(self.invoice_date_input)
        row2.addLayout(inv_date_layout)
        form_layout.addLayout(row2)

        # Batch and Quantity row
        row3 = QHBoxLayout()
        batch_layout = QVBoxLayout()
        batch_layout.addWidget(self.create_label("Batch Number"))
        self.batch_number_input = self.create_input("BATCH-001")
        batch_layout.addWidget(self.batch_number_input)
        row3.addLayout(batch_layout)

        expiry_layout = QVBoxLayout()
        expiry_layout.addWidget(self.create_label("Expiry Date"))
        self.expiry_date_input = QDateEdit()
        self.expiry_date_input.setDate(QDate.currentDate().addYears(1))
        self.expiry_date_input.setCalendarPopup(True)
        self.style_date(self.expiry_date_input)
        expiry_layout.addWidget(self.expiry_date_input)
        row3.addLayout(expiry_layout)
        form_layout.addLayout(row3)

        # Quantity row
        row3b = QHBoxLayout()
        qty_layout = QVBoxLayout()
        qty_layout.addWidget(self.create_label("Quantity"))
        self.quantity_input = self.create_input("0")
        self.quantity_input.textChanged.connect(self.calculate_taxes)
        qty_layout.addWidget(self.quantity_input)
        row3b.addLayout(qty_layout)
        form_layout.addLayout(row3b)

        # Amount
        form_layout.addWidget(self.create_label("Amount per Unit (₹)"))
        self.amount_input = self.create_input("0.00")
        self.amount_input.textChanged.connect(self.calculate_taxes)
        form_layout.addWidget(self.amount_input)

        # Tax percentages
        row4 = QHBoxLayout()
        cgst_layout = QVBoxLayout()
        cgst_layout.addWidget(self.create_label("CGST %"))
        self.cgst_percent_dropdown = QComboBox()
        self.cgst_percent_dropdown.addItem("0%", 0)
        self.cgst_percent_dropdown.addItem("5%", 5)
        self.cgst_percent_dropdown.addItem("9%", 9)
        self.cgst_percent_dropdown.addItem("18%", 18)
        self.style_combo(self.cgst_percent_dropdown)
        self.cgst_percent_dropdown.currentIndexChanged.connect(self.calculate_taxes)
        cgst_layout.addWidget(self.cgst_percent_dropdown)
        row4.addLayout(cgst_layout)

        sgst_layout = QVBoxLayout()
        sgst_layout.addWidget(self.create_label("SGST %"))
        self.sgst_percent_dropdown = QComboBox()
        self.sgst_percent_dropdown.addItem("0%", 0)
        self.sgst_percent_dropdown.addItem("5%", 5)
        self.sgst_percent_dropdown.addItem("9%", 9)
        self.sgst_percent_dropdown.addItem("18%", 18)
        self.style_combo(self.sgst_percent_dropdown)
        self.sgst_percent_dropdown.currentIndexChanged.connect(self.calculate_taxes)
        sgst_layout.addWidget(self.sgst_percent_dropdown)
        row4.addLayout(sgst_layout)
        form_layout.addLayout(row4)

        # Tax values (read-only)
        row5 = QHBoxLayout()
        cgst_val_layout = QVBoxLayout()
        cgst_val_layout.addWidget(self.create_label("CGST (₹)"))
        self.cgst_value_label = self.create_input("0.00", readonly=True)
        cgst_val_layout.addWidget(self.cgst_value_label)
        row5.addLayout(cgst_val_layout)

        sgst_val_layout = QVBoxLayout()
        sgst_val_layout.addWidget(self.create_label("SGST (₹)"))
        self.sgst_value_label = self.create_input("0.00", readonly=True)
        sgst_val_layout.addWidget(self.sgst_value_label)
        row5.addLayout(sgst_val_layout)

        round_layout = QVBoxLayout()
        round_layout.addWidget(self.create_label("Round Off (₹)"))
        self.round_off_label = self.create_input("0.00", readonly=True)
        round_layout.addWidget(self.round_off_label)
        row5.addLayout(round_layout)
        form_layout.addLayout(row5)

        # Net Amount
        form_layout.addWidget(self.create_label("Net Amount (₹)"))
        self.net_amount_label = self.create_input("0.00", readonly=True)
        self.net_amount_label.setStyleSheet("""
            QLineEdit {
                background-color: #E8F5E9;
                border: 2px solid #4CAF50;
                border-radius: 10px;
                padding: 15px;
                font-size: 18px;
                font-weight: bold;
                color: #2E7D32;
            }
        """)
        form_layout.addWidget(self.net_amount_label)

        # Save button
        save_btn = QPushButton("💾 Save Purchase")
        save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        save_btn.setStyleSheet("""
            QPushButton {
                background-color: #7B1FA2;
                color: white;
                border: none;
                border-radius: 10px;
                padding: 16px;
                font-size: 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #6A1B9A;
            }
        """)
        save_btn.clicked.connect(self.save_bill)
        form_layout.addWidget(save_btn)

        content_layout.addWidget(form_card, stretch=1)

        # Right Panel - Recent Bills
        list_card = self.create_card()
        list_layout = QVBoxLayout(list_card)
        list_layout.setContentsMargins(30, 30, 30, 30)
        list_layout.setSpacing(20)

        list_title = QLabel("Recent Bills")
        list_title.setStyleSheet("font-size: 20px; font-weight: bold; color: #1A1A2E; background: transparent;")
        list_layout.addWidget(list_title)

        self.bill_list = QListWidget()
        self.bill_list.setStyleSheet("""
            QListWidget {
                background-color: #F5F7FA;
                border: 2px solid #E0E6ED;
                border-radius: 10px;
                padding: 10px;
                font-size: 13px;
            }
            QListWidget::item {
                padding: 12px;
                border-bottom: 1px solid #E0E6ED;
            }
            QListWidget::item:selected {
                background-color: #F3E5F5;
                color: #7B1FA2;
            }
        """)
        list_layout.addWidget(self.bill_list)

        content_layout.addWidget(list_card, stretch=1)

        scroll.setWidget(content)
        main_layout.addWidget(scroll)

    def create_header(self, icon, title, subtitle):
        header = QFrame()
        header.setFixedHeight(100)
        header.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #6A1B9A, stop:1 #7B1FA2);
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

        close_btn = QPushButton("← Back")
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(255,255,255,0.2);
                color: white;
                border: 2px solid rgba(255,255,255,0.5);
                border-radius: 8px;
                padding: 10px 25px;
                font-size: 14px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: rgba(255,255,255,0.3);
            }
        """)
        close_btn.clicked.connect(self.close)
        header_layout.addWidget(close_btn)

        return header

    def create_card(self):
        card = QFrame()
        card.setStyleSheet("QFrame { background-color: white; border-radius: 16px; }")
        return card

    def create_label(self, text):
        label = QLabel(text)
        label.setStyleSheet("font-size: 14px; font-weight: 600; color: #1A1A2E; background: transparent;")
        return label

    def create_input(self, placeholder, readonly=False):
        inp = QLineEdit()
        inp.setPlaceholderText(placeholder)
        style = """
            QLineEdit {
                background-color: #F5F7FA;
                border: 2px solid #E0E6ED;
                border-radius: 10px;
                padding: 12px;
                font-size: 14px;
            }
            QLineEdit:focus {
                border: 2px solid #7B1FA2;
                background-color: white;
            }
        """
        if readonly:
            style = """
                QLineEdit {
                    background-color: #ECEFF1;
                    border: 2px solid #E0E6ED;
                    border-radius: 10px;
                    padding: 12px;
                    font-size: 14px;
                    color: #546E7A;
                }
            """
            inp.setReadOnly(True)
        inp.setStyleSheet(style)
        return inp

    def style_combo(self, combo):
        combo.setStyleSheet("""
            QComboBox {
                background-color: #F5F7FA;
                border: 2px solid #E0E6ED;
                border-radius: 10px;
                padding: 12px;
                font-size: 14px;
            }
            QComboBox:focus {
                border: 2px solid #7B1FA2;
            }
            QComboBox::drop-down {
                border: none;
                padding-right: 10px;
            }
            QComboBox QAbstractItemView {
                background-color: white;
                border: 2px solid #E0E6ED;
                selection-background-color: #7B1FA2;
                selection-color: white;
            }
        """)

    def style_date(self, date_edit):
        date_edit.setStyleSheet("""
            QDateEdit {
                background-color: #F5F7FA;
                border: 2px solid #E0E6ED;
                border-radius: 10px;
                padding: 12px;
                font-size: 14px;
            }
            QDateEdit:focus {
                border: 2px solid #7B1FA2;
            }
        """)

    def calculate_taxes(self):
        try:
            qty_text = self.quantity_input.text().strip()
            amount_text = self.amount_input.text().strip()
            
            if not qty_text or not amount_text:
                self.cgst_value_label.setText("")
                self.sgst_value_label.setText("")
                self.round_off_label.setText("")
                self.net_amount_label.setText("")
                return

            quantity = Decimal(qty_text)
            amount_per_unit = Decimal(amount_text)
            total_amount = quantity * amount_per_unit
            
            cgst_percent = Decimal(self.cgst_percent_dropdown.currentData() or 0)
            sgst_percent = Decimal(self.sgst_percent_dropdown.currentData() or 0)

            cgst_amount = (total_amount * cgst_percent / 100).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            sgst_amount = (total_amount * sgst_percent / 100).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

            subtotal = total_amount + cgst_amount + sgst_amount
            rounded_total = subtotal.quantize(Decimal('1'), rounding=ROUND_HALF_UP)
            round_off = rounded_total - subtotal

            self.cgst_value_label.setText(str(cgst_amount))
            self.sgst_value_label.setText(str(sgst_amount))
            self.round_off_label.setText(str(round_off))
            self.net_amount_label.setText(str(rounded_total))

        except Exception:
            self.cgst_value_label.setText("")
            self.sgst_value_label.setText("")
            self.round_off_label.setText("")
            self.net_amount_label.setText("")

    def load_vendors(self):
        self.vendor_dropdown.clear()
        vendors = self.vendor_service.get_all_vendors()
        if not vendors:
            self.vendor_dropdown.addItem("No vendors found", None)
            return
        for v in vendors:
            # Access by index for compatibility with packaged app
            vendor_id = v[0] if isinstance(v, (tuple, list)) else v["id"]
            vendor_name = v[1] if isinstance(v, (tuple, list)) else v["name"]
            self.vendor_dropdown.addItem(vendor_name, vendor_id)

    def load_items(self):
        self.item_dropdown.clear()
        items = self.item_service.get_all_items()
        if not items:
            self.item_dropdown.addItem("No items found", None)
            return
        for item in items:
            # Access by index for compatibility with packaged app
            item_id = item[0] if isinstance(item, (tuple, list)) else item["id"]
            item_name = item[1] if isinstance(item, (tuple, list)) else item["name"]
            self.item_dropdown.addItem(item_name, item_id)


    def save_bill(self):
        item_id = self.item_dropdown.currentData()
        vendor_id = self.vendor_dropdown.currentData()

        if vendor_id is None:
            QMessageBox.warning(self, "Error", "Please add/select a vendor first.")
            return

        if item_id is None:
            QMessageBox.warning(self, "Error", "Please add/select an item first.")
            return

        try:
            invoice_number = self.invoice_number_input.text().strip()
            invoice_date = self.invoice_date_input.date().toString("yyyy-MM-dd")
            batch_number = self.batch_number_input.text().strip()
            expiry_date = self.expiry_date_input.date().toString("yyyy-MM-dd")
            quantity = int(self.quantity_input.text() or 0)
            amount_per_unit = float(self.amount_input.text() or 0)
            total_amount = quantity * amount_per_unit
            cgst = float(self.cgst_value_label.text() or 0)
            sgst = float(self.sgst_value_label.text() or 0)
            round_off = float(self.round_off_label.text() or 0)
        except ValueError:
            QMessageBox.warning(self, "Error", "Please enter valid numeric values.")
            return

        if not invoice_number:
            QMessageBox.warning(self, "Error", "Please enter an invoice number.")
            return

        self.bill_service.add_bill(
            item_id=item_id,
            vendor_id=vendor_id,
            invoice_number=invoice_number,
            invoice_date=invoice_date,
            batch_number=batch_number,
            expiry_date=expiry_date,
            quantity=quantity,
            amount=total_amount,
            cgst=cgst,
            sgst=sgst,
            round_off=round_off
        )

        QMessageBox.information(self, "Success", "Bill saved successfully!")
        self.load_recent_bills()
        self.clear_inputs()

    def clear_inputs(self):
        self.invoice_number_input.clear()
        self.batch_number_input.clear()
        self.quantity_input.clear()
        self.amount_input.clear()
        self.cgst_percent_dropdown.setCurrentIndex(0)
        self.sgst_percent_dropdown.setCurrentIndex(0)
        self.cgst_value_label.clear()
        self.sgst_value_label.clear()
        self.round_off_label.clear()
        self.net_amount_label.clear()

    def load_recent_bills(self):
        self.bill_list.clear()
        bills = self.bill_service.get_recent_bills()
        for b in bills:
            self.bill_list.addItem(
                f"#{b['id']} | {b['entry_date']} | {b['vendor']} | {b['invoice_number']} | ₹{b['net_amount']}"
            )
