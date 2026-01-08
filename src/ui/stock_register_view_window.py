from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTableWidget,
    QTableWidgetItem, QHeaderView, QFileDialog, QMessageBox, QFrame,
    QLineEdit, QDateEdit, QComboBox
)
from PyQt6.QtCore import Qt, QDate
from PyQt6.QtPrintSupport import QPrinter, QPrintDialog
from PyQt6.QtGui import QTextDocument
import pandas as pd

from services.stock_service import StockService


class StockRegisterViewWindow(QWidget):
    """Window to display the complete stock register as a table with filters."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Stock Register View")
        self.setMinimumSize(1200, 800)
        self.setStyleSheet("background-color: #F5F7FA;")

        self.stock_service = StockService()
        self.last_data = None
        self.all_records = []  # Store all records for filtering

        self.init_ui()
        self.load_data()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Header
        header = self.create_header("📋", "Stock Register", "View current stock levels")
        main_layout.addWidget(header)

        # Content
        content = QWidget()
        content.setStyleSheet("background-color: #F5F7FA;")
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(40, 30, 40, 30)
        content_layout.setSpacing(20)

        # Filters Card
        filter_card = self.create_card()
        filter_card.setFixedHeight(80)
        filter_layout = QHBoxLayout(filter_card)
        filter_layout.setContentsMargins(20, 15, 20, 15)
        filter_layout.setSpacing(20)

        # Search
        search_label = QLabel("🔍 Search:")
        search_label.setStyleSheet("font-size: 14px; font-weight: 600; color: #1A1A2E; background: transparent;")
        filter_layout.addWidget(search_label)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search by item name...")
        self.search_input.setStyleSheet("""
            QLineEdit {
                background-color: #F5F7FA;
                border: 2px solid #E0E6ED;
                border-radius: 8px;
                padding: 10px 15px;
                font-size: 14px;
            }
            QLineEdit:focus {
                border: 2px solid #00695C;
            }
        """)
        self.search_input.textChanged.connect(self.filter_data)
        self.search_input.setFixedWidth(250)
        filter_layout.addWidget(self.search_input)

        filter_layout.addStretch()

        # Balance filter
        balance_label = QLabel("Balance:")
        balance_label.setStyleSheet("font-size: 14px; font-weight: 600; color: #1A1A2E; background: transparent;")
        filter_layout.addWidget(balance_label)

        self.balance_filter = QComboBox()
        self.balance_filter.addItem("All Items", "all")
        self.balance_filter.addItem("Low Stock (< 10)", "low")
        self.balance_filter.addItem("Out of Stock (0)", "out")
        self.balance_filter.addItem("In Stock (> 0)", "in")
        self.balance_filter.setStyleSheet("""
            QComboBox {
                background-color: #F5F7FA;
                border: 2px solid #E0E6ED;
                border-radius: 8px;
                padding: 10px 15px;
                font-size: 14px;
            }
        """)
        self.balance_filter.currentIndexChanged.connect(self.filter_data)
        filter_layout.addWidget(self.balance_filter)

        content_layout.addWidget(filter_card)

        # Table Card
        table_card = self.create_card()
        table_layout = QVBoxLayout(table_card)
        table_layout.setContentsMargins(20, 20, 20, 20)

        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels([
            "Sr. No.", "Lab Items", "Received Qty.", "Issued Qty.", "Balance Qty."
        ])
        self.table.setStyleSheet("""
            QTableWidget {
                background-color: white;
                border: none;
                gridline-color: #E0E6ED;
                font-size: 14px;
            }
            QTableWidget::item {
                padding: 15px;
                border-bottom: 1px solid #E0E6ED;
            }
            QTableWidget::item:selected {
                background-color: #E0F2F1;
                color: #00695C;
            }
            QHeaderView::section {
                background-color: #00695C;
                color: white;
                padding: 15px;
                font-weight: bold;
                font-size: 14px;
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

        refresh_btn = self.create_button("🔄 Refresh", "#00695C", self.load_data)
        export_btn = self.create_button("📊 Export to Excel", "#1565C0", self.export_to_excel)
        print_btn = self.create_button("🖨️ Print", "#7B1FA2", self.print_report)
        close_btn = self.create_button("← Back", "#546E7A", self.close)

        btn_layout.addWidget(refresh_btn)
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
                    stop:0 #004D40, stop:1 #00695C);
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
                padding: 14px 28px;
                font-size: 14px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background-color: {color}DD;
            }}
        """)
        btn.clicked.connect(callback)
        return btn

    def load_data(self):
        self.all_records = self.stock_service.get_stock_register_view()
        self.filter_data()

    def filter_data(self):
        """Filter records based on search and balance filter."""
        search_text = self.search_input.text().lower().strip()
        balance_filter = self.balance_filter.currentData()

        filtered = []
        for record in self.all_records:
            # Search filter
            if search_text and search_text not in record['lab_item'].lower():
                continue

            # Balance filter
            balance = record['balance_qty']
            if balance_filter == "low" and balance >= 10:
                continue
            if balance_filter == "out" and balance != 0:
                continue
            if balance_filter == "in" and balance <= 0:
                continue

            filtered.append(record)

        self.display_records(filtered)

    def display_records(self, records):
        self.table.setRowCount(len(records))

        data_for_export = []

        for row_idx, record in enumerate(records):
            self.table.setItem(row_idx, 0, QTableWidgetItem(str(record['sr_no'])))
            self.table.setItem(row_idx, 1, QTableWidgetItem(record['lab_item']))
            self.table.setItem(row_idx, 2, QTableWidgetItem(str(record['received_qty'])))
            self.table.setItem(row_idx, 3, QTableWidgetItem(str(record['issued_qty'])))

            # Color code balance
            balance_item = QTableWidgetItem(str(record['balance_qty']))
            if record['balance_qty'] <= 0:
                balance_item.setForeground(Qt.GlobalColor.red)
            elif record['balance_qty'] < 10:
                balance_item.setForeground(Qt.GlobalColor.darkYellow)
            else:
                balance_item.setForeground(Qt.GlobalColor.darkGreen)
            self.table.setItem(row_idx, 4, balance_item)

            data_for_export.append({
                'Sr. No.': record['sr_no'],
                'Lab Items': record['lab_item'],
                'Received Qty.': record['received_qty'],
                'Issued Qty.': record['issued_qty'],
                'Balance Qty.': record['balance_qty']
            })

        self.last_data = data_for_export

        if not records:
            self.table.setRowCount(1)
            self.table.setItem(0, 0, QTableWidgetItem("No data found"))
            self.table.setSpan(0, 0, 1, 5)

    def export_to_excel(self):
        if not self.last_data:
            QMessageBox.warning(self, "Error", "No data to export")
            return

        path, _ = QFileDialog.getSaveFileName(
            self, "Save Stock Register", "", "Excel Files (*.xlsx)"
        )

        if path:
            df = pd.DataFrame(self.last_data)
            df.to_excel(path, index=False)
            QMessageBox.information(self, "Success", "Stock register exported successfully!")

    def print_report(self):
        """Print the stock register."""
        if not self.last_data:
            QMessageBox.warning(self, "Error", "No data to print")
            return

        printer = QPrinter(QPrinter.PrinterMode.HighResolution)
        dialog = QPrintDialog(printer, self)

        if dialog.exec() == QPrintDialog.DialogCode.Accepted:
            # Create HTML content
            html = """
            <html>
            <head>
                <style>
                    body { font-family: Arial, sans-serif; }
                    h1 { text-align: center; color: #00695C; }
                    table { width: 100%; border-collapse: collapse; margin-top: 20px; }
                    th { background-color: #00695C; color: white; padding: 10px; text-align: left; }
                    td { padding: 8px; border-bottom: 1px solid #ddd; }
                    tr:nth-child(even) { background-color: #f2f2f2; }
                    .low { color: orange; }
                    .out { color: red; }
                </style>
            </head>
            <body>
                <h1>Stock Register</h1>
                <table>
                    <tr>
                        <th>Sr. No.</th>
                        <th>Lab Items</th>
                        <th>Received Qty.</th>
                        <th>Issued Qty.</th>
                        <th>Balance Qty.</th>
                    </tr>
            """

            for item in self.last_data:
                balance_class = ""
                if item['Balance Qty.'] <= 0:
                    balance_class = "out"
                elif item['Balance Qty.'] < 10:
                    balance_class = "low"

                html += f"""
                    <tr>
                        <td>{item['Sr. No.']}</td>
                        <td>{item['Lab Items']}</td>
                        <td>{item['Received Qty.']}</td>
                        <td>{item['Issued Qty.']}</td>
                        <td class="{balance_class}">{item['Balance Qty.']}</td>
                    </tr>
                """

            html += "</table></body></html>"

            doc = QTextDocument()
            doc.setHtml(html)
            doc.print_(printer)
            QMessageBox.information(self, "Success", "Print job sent!")
