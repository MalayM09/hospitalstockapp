from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTableWidget,
    QTableWidgetItem, QHeaderView, QFileDialog, QMessageBox, QFrame,
    QLineEdit, QDateEdit, QDialog, QComboBox, QGridLayout
)
from PyQt6.QtCore import Qt, QDate
from PyQt6.QtPrintSupport import QPrinter, QPrintDialog
from PyQt6.QtGui import QTextDocument
import pandas as pd
from datetime import datetime

from services.stock_service import StockService, StockError
from services.item_service import ItemService


class StockIssuanceRegisterWindow(QWidget):
    """Window to display stock issuance history with date filters."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Stock Issuance Register")
        self.setMinimumSize(1200, 800)
        self.setStyleSheet("background-color: #F5F7FA;")

        self.stock_service = StockService()
        self.last_data = None
        self.all_records = []

        self.init_ui()
        self.load_data()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Header
        header = self.create_header("📑", "Stock Issuance Register", "View lab stock issuance history")
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
                border: 2px solid #C62828;
            }
        """)
        self.search_input.textChanged.connect(self.filter_data)
        self.search_input.setFixedWidth(200)
        filter_layout.addWidget(self.search_input)

        filter_layout.addStretch()

        # Date Range Filters
        from_label = QLabel("From:")
        from_label.setStyleSheet("font-size: 14px; font-weight: 600; color: #1A1A2E; background: transparent;")
        filter_layout.addWidget(from_label)

        self.from_date = QDateEdit()
        self.from_date.setDate(QDate.currentDate().addMonths(-1))
        self.from_date.setCalendarPopup(True)
        self.from_date.setStyleSheet("""
            QDateEdit {
                background-color: #F5F7FA;
                border: 2px solid #E0E6ED;
                border-radius: 8px;
                padding: 10px 15px;
                font-size: 14px;
            }
        """)
        self.from_date.dateChanged.connect(self.filter_data)
        filter_layout.addWidget(self.from_date)

        to_label = QLabel("To:")
        to_label.setStyleSheet("font-size: 14px; font-weight: 600; color: #1A1A2E; background: transparent;")
        filter_layout.addWidget(to_label)

        self.to_date = QDateEdit()
        self.to_date.setDate(QDate.currentDate())
        self.to_date.setCalendarPopup(True)
        self.to_date.setStyleSheet("""
            QDateEdit {
                background-color: #F5F7FA;
                border: 2px solid #E0E6ED;
                border-radius: 8px;
                padding: 10px 15px;
                font-size: 14px;
            }
        """)
        self.to_date.dateChanged.connect(self.filter_data)
        filter_layout.addWidget(self.to_date)

        # Clear filters button
        clear_btn = QPushButton("Clear")
        clear_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        clear_btn.setStyleSheet("""
            QPushButton {
                background-color: #9E9E9E;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 10px 20px;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #757575;
            }
        """)
        clear_btn.clicked.connect(self.clear_filters)
        filter_layout.addWidget(clear_btn)

        content_layout.addWidget(filter_card)

        # Table Card
        table_card = self.create_card()
        table_layout = QVBoxLayout(table_card)
        table_layout.setContentsMargins(20, 20, 20, 20)

        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels([
            "Entry ID", "Date", "Item Name", "Quantity Issued", "Remarks"
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
                background-color: #FFEBEE;
                color: #C62828;
            }
            QHeaderView::section {
                background-color: #C62828;
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

        refresh_btn = self.create_button("🔄 Refresh", "#C62828", self.load_data)
        edit_btn = self.create_button("✏️ Edit Selected", "#1565C0", self.edit_selected)
        delete_btn = self.create_button("🗑️ Delete Selected", "#B71C1C", self.delete_selected)
        export_btn = self.create_button("📊 Export to Excel", "#1565C0", self.export_to_excel)
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
                    stop:0 #B71C1C, stop:1 #C62828);
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

    def clear_filters(self):
        """Clear all filters and reload data."""
        self.search_input.clear()
        self.from_date.setDate(QDate.currentDate().addMonths(-1))
        self.to_date.setDate(QDate.currentDate())
        self.load_data()

    def load_data(self):
        """Load data from database."""
        start_date = self.from_date.date().toString("yyyy-MM-dd")
        end_date = self.to_date.date().toString("yyyy-MM-dd")
        search_term = self.search_input.text().strip() or None

        self.all_records = self.stock_service.get_stock_issuance_history(
            start_date=start_date,
            end_date=end_date,
            search_term=search_term
        )
        self.display_records(self.all_records)

    def filter_data(self):
        """Filter and reload data based on current filter values."""
        self.load_data()

    def display_records(self, records):
        self.table.clearSpans()  # a previous "No data found" row may have merged cells
        self.table.setRowCount(len(records))

        data_for_export = []

        for row_idx, record in enumerate(records):
            self.table.setItem(row_idx, 0, QTableWidgetItem(str(record['sr_no'])))
            self.table.setItem(row_idx, 1, QTableWidgetItem(str(record['date'] or '-')))
            self.table.setItem(row_idx, 2, QTableWidgetItem(record['item_name']))

            # Quantity with styling
            qty_item = QTableWidgetItem(str(record['issued_qty']))
            qty_item.setForeground(Qt.GlobalColor.darkRed)
            self.table.setItem(row_idx, 3, qty_item)
            self.table.setItem(row_idx, 4, QTableWidgetItem(record['remarks']))

            data_for_export.append({
                'Sr. No.': record['sr_no'],
                'Date': record['date'],
                'Item Name': record['item_name'],
                'Quantity Issued': record['issued_qty'],
                'Remarks': record['remarks'],
            })

        self.last_data = data_for_export

        if not records:
            self.table.setRowCount(1)
            self.table.setItem(0, 0, QTableWidgetItem("No data found"))
            self.table.setSpan(0, 0, 1, self.table.columnCount())

    def get_selected_id(self):
        row = self.table.currentRow()
        if row < 0:
            return None
        item = self.table.item(row, 0)
        return int(item.text()) if item and item.text().isdigit() else None

    def edit_selected(self):
        stock_id = self.get_selected_id()
        if stock_id is None:
            QMessageBox.warning(self, "Error", "Please select an issue entry to edit")
            return
        entry = self.stock_service.get_issue(stock_id)
        if not entry:
            QMessageBox.warning(self, "Error", "That entry no longer exists")
            self.load_data()
            return
        dialog = EditIssueDialog(entry, self)
        while dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_data()
            if data is None:
                continue
            try:
                self.stock_service.update_issue(stock_id, **data)
            except StockError as e:
                QMessageBox.warning(self, "Cannot Save", str(e))
                continue
            QMessageBox.information(self, "Success", "Issue entry updated.")
            self.load_data()
            break

    def delete_selected(self):
        stock_id = self.get_selected_id()
        if stock_id is None:
            QMessageBox.warning(self, "Error", "Please select an issue entry to delete")
            return
        entry = self.stock_service.get_issue(stock_id)
        if not entry:
            self.load_data()
            return
        reply = QMessageBox.question(
            self, "Confirm Delete",
            f"Delete this issue entry?\n\n{entry['date']}  ·  {entry['item_name']}  ·  "
            f"{entry['issued_qty']} units\n\nThe quantity will be added back to stock.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            try:
                self.stock_service.delete_issue(stock_id)
            except StockError as e:
                QMessageBox.warning(self, "Cannot Delete", str(e))
                return
            self.load_data()

    def export_to_excel(self):
        if not self.last_data:
            QMessageBox.warning(self, "Error", "No data to export")
            return

        path, _ = QFileDialog.getSaveFileName(
            self, "Save Stock Issuance Register", "", "Excel Files (*.xlsx)"
        )

        if path:
            df = pd.DataFrame(self.last_data)
            df.to_excel(path, index=False)
            QMessageBox.information(self, "Success", "Stock issuance register exported successfully!")

    def print_report(self):
        """Print the stock issuance register."""
        if not self.last_data:
            QMessageBox.warning(self, "Error", "No data to print")
            return

        printer = QPrinter(QPrinter.PrinterMode.HighResolution)
        dialog = QPrintDialog(printer, self)

        if dialog.exec() == QPrintDialog.DialogCode.Accepted:
            # Create HTML content
            html = f"""
            <html>
            <head>
                <style>
                    body {{ font-family: Arial, sans-serif; }}
                    h1 {{ text-align: center; color: #C62828; }}
                    table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
                    th {{ background-color: #C62828; color: white; padding: 10px; text-align: left; }}
                    td {{ padding: 8px; border-bottom: 1px solid #ddd; }}
                    tr:nth-child(even) {{ background-color: #f2f2f2; }}
                    .date {{ font-size: 12px; color: #666; text-align: center; }}
                    .issued {{ color: #C62828; }}
                </style>
            </head>
            <body>
                <h1>Stock Issuance Register</h1>
                <p class="date">Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}</p>
                <p class="date">Period: {self.from_date.date().toString('yyyy-MM-dd')} to {self.to_date.date().toString('yyyy-MM-dd')}</p>
                <table>
                    <tr>
                        <th>Sr. No.</th>
                        <th>Date</th>
                        <th>Item Name</th>
                        <th>Qty Issued</th>
                    </tr>
            """

            for item in self.last_data:
                html += f"""
                    <tr>
                        <td>{item['Sr. No.']}</td>
                        <td>{item['Date']}</td>
                        <td>{item['Item Name']}</td>
                        <td class="issued">{item['Quantity Issued']}</td>
                    </tr>
                """

            html += "</table></body></html>"

            doc = QTextDocument()
            doc.setHtml(html)
            doc.print_(printer)
            QMessageBox.information(self, "Success", "Print job sent!")


class EditIssueDialog(QDialog):
    """Correct the item, quantity, date or remarks of an issue entry."""

    def __init__(self, entry, parent=None):
        super().__init__(parent)
        self.entry = entry
        self.setWindowTitle(f"Edit Issue Entry #{entry['id']}")
        self.setMinimumWidth(460)
        self.setStyleSheet("background-color: white;")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(15)
        title = QLabel(f"Edit Issue Entry #{entry['id']}")
        title.setStyleSheet("font-size: 20px; font-weight: bold; color: #C62828;")
        layout.addWidget(title)

        grid = QGridLayout()
        grid.setSpacing(10)

        self.item_combo = QComboBox()
        for i in ItemService().get_all_items():
            self.item_combo.addItem(i['name'], i['id'])
        self.item_combo.setCurrentIndex(max(0, self.item_combo.findData(entry['item_id'])))

        self.qty_input = QLineEdit(str(entry['issued_qty']))

        self.date_input = QDateEdit()
        self.date_input.setDisplayFormat("dd-MM-yyyy")
        self.date_input.setCalendarPopup(True)
        self.date_input.setMaximumDate(QDate.currentDate())
        self.date_input.setDate(QDate.fromString(entry['date'], "yyyy-MM-dd") if entry['date']
                                else QDate.currentDate())

        self.remarks_input = QLineEdit(entry.get('remarks') or '')

        for row, (label, widget) in enumerate([
            ("Item", self.item_combo), ("Quantity", self.qty_input),
            ("Issue Date", self.date_input), ("Remarks", self.remarks_input),
        ]):
            lbl = QLabel(label)
            lbl.setStyleSheet("font-size: 13px; font-weight: 600; color: #333;")
            grid.addWidget(lbl, row, 0)
            grid.addWidget(widget, row, 1)
        layout.addLayout(grid)

        buttons = QHBoxLayout()
        save = QPushButton("💾 Save")
        save.setStyleSheet("""
            QPushButton { background-color: #C62828; color: white; border: none; border-radius: 8px;
                          padding: 12px 30px; font-weight: bold; }
            QPushButton:hover { background-color: #B71C1C; }
        """)
        save.clicked.connect(self.accept)
        cancel = QPushButton("Cancel")
        cancel.setStyleSheet("""
            QPushButton { background-color: #9E9E9E; color: white; border: none; border-radius: 8px;
                          padding: 12px 30px; }
            QPushButton:hover { background-color: #757575; }
        """)
        cancel.clicked.connect(self.reject)
        buttons.addWidget(save)
        buttons.addWidget(cancel)
        layout.addLayout(buttons)

    def get_data(self):
        qty = self.qty_input.text().strip()
        if not qty.isdigit() or int(qty) <= 0:
            QMessageBox.warning(self, "Error", "Quantity must be a whole number greater than zero.")
            return None
        return {
            'item_id': self.item_combo.currentData(),
            'qty': int(qty),
            'issue_date': self.date_input.date().toString("yyyy-MM-dd"),
            'remarks': self.remarks_input.text().strip(),
        }
