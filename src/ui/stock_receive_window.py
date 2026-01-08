from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QComboBox,
    QLineEdit, QPushButton, QMessageBox, QListWidget, QDateEdit
)
from PyQt6.QtCore import Qt, QDate

from services.stock_service import StockService
from services.item_service import ItemService
from services.vendor_service import VendorService


class StockReceiveWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Stock Receive")
        self.setFixedSize(450, 500)

        self.stock_service = StockService()
        self.item_service = ItemService()
        self.vendor_service = VendorService()

        self.init_ui()
        self.load_vendors()
        self.load_items()
        self.load_stock_entries()

    def init_ui(self):
        layout = QVBoxLayout()

        # Vendor selection
        layout.addWidget(QLabel("Select Vendor:"))
        self.vendor_dropdown = QComboBox()
        layout.addWidget(self.vendor_dropdown)

        # Item selection
        layout.addWidget(QLabel("Select Item:"))
        self.item_dropdown = QComboBox()
        layout.addWidget(self.item_dropdown)

        # Quantity input
        layout.addWidget(QLabel("Quantity Received:"))
        self.qty_input = QLineEdit()
        self.qty_input.setPlaceholderText("Enter quantity")
        layout.addWidget(self.qty_input)

        # Date picker
        layout.addWidget(QLabel("Date:"))
        self.date_input = QDateEdit()
        self.date_input.setDate(QDate.currentDate())
        self.date_input.setCalendarPopup(True)
        layout.addWidget(self.date_input)

        # Buttons
        btn_add = QPushButton("Add Stock Entry")
        btn_add.clicked.connect(self.save_entry)
        layout.addWidget(btn_add)

        # List to show stock received entries
        layout.addWidget(QLabel("Recent Stock Received:"))
        self.entry_list = QListWidget()
        layout.addWidget(self.entry_list)

        self.setLayout(layout)

    def load_vendors(self):
        self.vendor_dropdown.clear()
        vendors = self.vendor_service.get_all_vendors()
        for v in vendors:
            self.vendor_dropdown.addItem(v["name"], v["id"])

    def load_items(self):
        self.item_dropdown.clear()
        items = self.item_service.get_all_items()
        for item in items:
            self.item_dropdown.addItem(item["name"], item["id"])

    def save_entry(self):
        item_id = self.item_dropdown.currentData()
        vendor_id = self.vendor_dropdown.currentData()
        qty_text = self.qty_input.text().strip()

        if item_id is None:
            QMessageBox.warning(self, "Error", "Please select an item")
            return

        if vendor_id is None:
            QMessageBox.warning(self, "Error", "Please select a vendor")
            return

        if not qty_text.isdigit() or int(qty_text) <= 0:
            QMessageBox.warning(self, "Error", "Enter a valid quantity")
            return

        qty = int(qty_text)

        # Use stock service to record received stock
        self.stock_service.receive_stock(item_id, vendor_id, qty)

        QMessageBox.information(self, "Success", "Stock entry added")
        self.qty_input.clear()
        self.load_stock_entries()

    def load_stock_entries(self):
        self.entry_list.clear()
        entries = self.stock_service.get_stock_history()

        for e in entries:
            if e['received_qty'] > 0:  # Only show received entries
                self.entry_list.addItem(
                    f"{e['date']} | {e['item_name']} | {e['received_qty']} units | From: {e['vendor_name'] or 'N/A'}"
                )
