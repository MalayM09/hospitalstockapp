from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QListWidget,
    QFileDialog, QMessageBox, QFrame, QGridLayout, QDateEdit
)
from PyQt6.QtCore import Qt, QDate
from PyQt6.QtPrintSupport import QPrinter, QPrintDialog
from PyQt6.QtGui import QTextDocument
import pandas as pd
from datetime import datetime, timedelta

from services.db_service import DatabaseService
from services.stock_service import StockService


class ReportsWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Reports")
        self.setMinimumSize(1200, 800)
        self.setStyleSheet("background-color: #F5F7FA;")

        self.db = DatabaseService()
        self.stock_service = StockService()
        self.last_report_df = None
        self.last_report_title = "Report"

        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Header
        header = self.create_header("📊", "Reports Dashboard", "Generate and export reports")
        main_layout.addWidget(header)

        # Content
        content = QWidget()
        content.setStyleSheet("background-color: #F5F7FA;")
        content_layout = QHBoxLayout(content)
        content_layout.setContentsMargins(40, 40, 40, 40)
        content_layout.setSpacing(30)

        # Left Panel - Report Buttons & Filters
        btn_card = self.create_card()
        btn_layout = QVBoxLayout(btn_card)
        btn_layout.setContentsMargins(30, 30, 30, 30)
        btn_layout.setSpacing(15)

        # Date Filters
        date_title = QLabel("📅 Date Range")
        date_title.setStyleSheet("font-size: 18px; font-weight: bold; color: #1A1A2E; background: transparent;")
        btn_layout.addWidget(date_title)

        date_row = QHBoxLayout()
        
        from_layout = QVBoxLayout()
        from_label = QLabel("From:")
        from_label.setStyleSheet("font-size: 13px; color: #546E7A; background: transparent;")
        from_layout.addWidget(from_label)
        self.from_date = QDateEdit()
        self.from_date.setDate(QDate.currentDate().addMonths(-1))
        self.from_date.setCalendarPopup(True)
        self.style_date(self.from_date)
        from_layout.addWidget(self.from_date)
        date_row.addLayout(from_layout)

        to_layout = QVBoxLayout()
        to_label = QLabel("To:")
        to_label.setStyleSheet("font-size: 13px; color: #546E7A; background: transparent;")
        to_layout.addWidget(to_label)
        self.to_date = QDateEdit()
        self.to_date.setDate(QDate.currentDate())
        self.to_date.setCalendarPopup(True)
        self.style_date(self.to_date)
        to_layout.addWidget(self.to_date)
        date_row.addLayout(to_layout)

        btn_layout.addLayout(date_row)

        # Separator
        sep = QFrame()
        sep.setFixedHeight(2)
        sep.setStyleSheet("background-color: #E0E6ED;")
        btn_layout.addWidget(sep)

        btn_title = QLabel("📋 Select Report Type")
        btn_title.setStyleSheet("font-size: 18px; font-weight: bold; color: #1A1A2E; background: transparent; padding-top: 10px;")
        btn_layout.addWidget(btn_title)

        # Report buttons
        report_buttons = [
            ("📅 Daily Report", "#1976D2", self.show_daily_report),
            ("📆 Weekly Report", "#7B1FA2", self.show_weekly_report),
            ("🗓️ Monthly Report", "#00897B", self.show_monthly_report),
            ("📦 Stock Summary", "#E65100", self.show_stock_summary),
            ("🏢 Vendor-wise Report", "#C62828", self.show_vendor_report),
        ]

        for text, color, callback in report_buttons:
            btn = self.create_report_button(text, color, callback)
            btn_layout.addWidget(btn)

        btn_layout.addStretch()

        # Action buttons row
        action_row = QHBoxLayout()
        
        export_btn = QPushButton("📥 Export")
        export_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        export_btn.setStyleSheet("""
            QPushButton {
                background-color: #2E7D32;
                color: white;
                border: none;
                border-radius: 10px;
                padding: 14px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1B5E20;
            }
        """)
        export_btn.clicked.connect(self.export_to_excel)
        action_row.addWidget(export_btn)

        print_btn = QPushButton("🖨️ Print")
        print_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        print_btn.setStyleSheet("""
            QPushButton {
                background-color: #7B1FA2;
                color: white;
                border: none;
                border-radius: 10px;
                padding: 14px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #6A1B9A;
            }
        """)
        print_btn.clicked.connect(self.print_report)
        action_row.addWidget(print_btn)

        btn_layout.addLayout(action_row)

        content_layout.addWidget(btn_card, stretch=1)

        # Right Panel - Results
        result_card = self.create_card()
        result_layout = QVBoxLayout(result_card)
        result_layout.setContentsMargins(30, 30, 30, 30)
        result_layout.setSpacing(20)

        self.result_title = QLabel("Report Results")
        self.result_title.setStyleSheet("font-size: 20px; font-weight: bold; color: #1A1A2E; background: transparent;")
        result_layout.addWidget(self.result_title)

        self.list_widget = QListWidget()
        self.list_widget.setStyleSheet("""
            QListWidget {
                background-color: #F5F7FA;
                border: 2px solid #E0E6ED;
                border-radius: 10px;
                padding: 10px;
                font-size: 14px;
                font-family: 'Courier New', monospace;
            }
            QListWidget::item {
                padding: 12px;
                border-bottom: 1px solid #E0E6ED;
            }
            QListWidget::item:selected {
                background-color: #E3F2FD;
                color: #1565C0;
            }
        """)
        result_layout.addWidget(self.list_widget)

        content_layout.addWidget(result_card, stretch=2)
        main_layout.addWidget(content)

    def create_header(self, icon, title, subtitle):
        header = QFrame()
        header.setFixedHeight(100)
        header.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #0D47A1, stop:1 #1976D2);
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

    def style_date(self, date_edit):
        date_edit.setStyleSheet("""
            QDateEdit {
                background-color: #F5F7FA;
                border: 2px solid #E0E6ED;
                border-radius: 8px;
                padding: 10px;
                font-size: 14px;
            }
            QDateEdit:focus {
                border: 2px solid #1976D2;
            }
        """)

    def create_report_button(self, text, color, callback):
        btn = QPushButton(text)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: white;
                color: {color};
                border: 2px solid {color};
                border-radius: 10px;
                padding: 14px;
                font-size: 14px;
                font-weight: 600;
                text-align: left;
            }}
            QPushButton:hover {{
                background-color: {color};
                color: white;
            }}
        """)
        btn.clicked.connect(callback)
        return btn

    def get_date_range(self):
        """Get selected date range as strings."""
        from_str = self.from_date.date().toString("yyyy-MM-dd")
        to_str = self.to_date.date().toString("yyyy-MM-dd")
        return from_str, to_str

    def show_daily_report(self):
        from_date, to_date = self.get_date_range()
        query = f"""
        SELECT entry_date as Date, SUM(net_amount) AS Total_Spent
        FROM bills
        WHERE entry_date BETWEEN '{from_date}' AND '{to_date}'
        GROUP BY entry_date
        ORDER BY entry_date DESC
        """
        self.last_report_title = f"Daily Report ({from_date} to {to_date})"
        self.result_title.setText(self.last_report_title)
        self.generate_report(query)

    def show_weekly_report(self):
        from_date, to_date = self.get_date_range()
        query = f"""
        SELECT STRFTIME('%Y-%W', entry_date) AS Week, SUM(net_amount) AS Total_Spent
        FROM bills
        WHERE entry_date BETWEEN '{from_date}' AND '{to_date}'
        GROUP BY Week
        ORDER BY Week DESC
        """
        self.last_report_title = f"Weekly Report ({from_date} to {to_date})"
        self.result_title.setText(self.last_report_title)
        self.generate_report(query)

    def show_monthly_report(self):
        from_date, to_date = self.get_date_range()
        query = f"""
        SELECT STRFTIME('%Y-%m', entry_date) AS Month, SUM(net_amount) AS Total_Spent
        FROM bills
        WHERE entry_date BETWEEN '{from_date}' AND '{to_date}'
        GROUP BY Month
        ORDER BY Month DESC
        """
        self.last_report_title = f"Monthly Report ({from_date} to {to_date})"
        self.result_title.setText(self.last_report_title)
        self.generate_report(query)

    def show_stock_summary(self):
        self.list_widget.clear()
        self.last_report_title = "Stock Summary"
        self.result_title.setText(self.last_report_title)
        
        balances = self.stock_service.get_all_balances()

        if not balances:
            self.list_widget.addItem("No stock data found")
            return

        data = []
        for b in balances:
            line = f"{b['name']:<40} | Recv: {b['total_received']:>6} | Issue: {b['total_issued']:>6} | Bal: {b['balance']:>6}"
            self.list_widget.addItem(line)
            data.append({
                'Item': b['name'],
                'Total Received': b['total_received'],
                'Total Issued': b['total_issued'],
                'Balance': b['balance']
            })

        self.last_report_df = pd.DataFrame(data)

    def show_vendor_report(self):
        from_date, to_date = self.get_date_range()
        query = f"""
        SELECT v.name AS Vendor, COUNT(b.id) AS Bills, SUM(b.net_amount) AS Total_Spent
        FROM bills b
        JOIN vendors v ON b.vendor_id = v.id
        WHERE b.entry_date BETWEEN '{from_date}' AND '{to_date}'
        GROUP BY v.id
        ORDER BY Total_Spent DESC
        """
        self.last_report_title = f"Vendor Report ({from_date} to {to_date})"
        self.result_title.setText(self.last_report_title)
        self.generate_report(query)

    def generate_report(self, query):
        records = self.db.fetch_all(query)
        self.list_widget.clear()

        if not records:
            self.list_widget.addItem("No data found for selected date range")
            return

        data = [dict(row) for row in records]
        self.last_report_df = pd.DataFrame(data)

        # Add header
        if data:
            headers = " | ".join([f"{k:<15}" for k in data[0].keys()])
            self.list_widget.addItem(headers)
            self.list_widget.addItem("-" * len(headers))

        for row in records:
            line = " | ".join([f"{str(v):<15}" for v in row])
            self.list_widget.addItem(line)

    def export_to_excel(self):
        if self.last_report_df is None:
            QMessageBox.warning(self, "Error", "Generate a report first")
            return

        path, _ = QFileDialog.getSaveFileName(self, "Save Report", "", "Excel Files (*.xlsx)")

        if path:
            self.last_report_df.to_excel(path, index=False)
            QMessageBox.information(self, "Success", "Report exported successfully!")

    def print_report(self):
        """Print the current report."""
        if self.last_report_df is None or self.last_report_df.empty:
            QMessageBox.warning(self, "Error", "Generate a report first")
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
                    h1 {{ text-align: center; color: #1976D2; }}
                    table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
                    th {{ background-color: #1976D2; color: white; padding: 10px; text-align: left; }}
                    td {{ padding: 8px; border-bottom: 1px solid #ddd; }}
                    tr:nth-child(even) {{ background-color: #f2f2f2; }}
                    .date {{ font-size: 12px; color: #666; text-align: center; }}
                </style>
            </head>
            <body>
                <h1>{self.last_report_title}</h1>
                <p class="date">Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}</p>
                <table>
                    <tr>
            """

            # Add headers
            for col in self.last_report_df.columns:
                html += f"<th>{col}</th>"
            html += "</tr>"

            # Add rows
            for _, row in self.last_report_df.iterrows():
                html += "<tr>"
                for val in row:
                    html += f"<td>{val}</td>"
                html += "</tr>"

            html += "</table></body></html>"

            doc = QTextDocument()
            doc.setHtml(html)
            doc.print_(printer)
            QMessageBox.information(self, "Success", "Print job sent!")
