from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QLineEdit, QPushButton, QMessageBox, QListWidget, QFrame, QDateEdit
)
from PyQt6.QtCore import Qt, QDate

from services.stock_service import StockService, StockError
from services.item_service import ItemService


class StockIssueWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Stock Issue")
        self.setMinimumSize(1200, 800)
        self.setStyleSheet("background-color: #F5F7FA;")

        self.stock_service = StockService()
        self.item_service = ItemService()

        self.init_ui()
        self.load_items()
        self.load_stock_issued()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Header
        header = self.create_header("📤", "Stock Issue", "Issue stock for lab use")
        main_layout.addWidget(header)

        # Content
        content = QWidget()
        content.setStyleSheet("background-color: #F5F7FA;")
        content_layout = QHBoxLayout(content)
        content_layout.setContentsMargins(40, 40, 40, 40)
        content_layout.setSpacing(30)

        # Left Panel - Form
        form_card = self.create_card()
        form_layout = QVBoxLayout(form_card)
        form_layout.setContentsMargins(30, 30, 30, 30)
        form_layout.setSpacing(20)

        form_title = QLabel("Issue Stock for Lab Use")
        form_title.setStyleSheet("font-size: 20px; font-weight: bold; color: #1A1A2E; background: transparent;")
        form_layout.addWidget(form_title)

        # Item
        form_layout.addWidget(self.create_label("Select Item"))
        self.item_dropdown = QComboBox()
        self.style_combo(self.item_dropdown)
        self.item_dropdown.currentIndexChanged.connect(self.update_balance_display)
        form_layout.addWidget(self.item_dropdown)

        # Balance display
        self.balance_label = QLabel("Available Balance: --")
        self.balance_label.setStyleSheet("""
            font-size: 18px;
            font-weight: bold;
            color: #1565C0;
            background-color: #E3F2FD;
            padding: 20px;
            border-radius: 10px;
        """)
        form_layout.addWidget(self.balance_label)

        # Quantity
        form_layout.addWidget(self.create_label("Quantity to Issue"))
        self.qty_input = QLineEdit()
        self.qty_input.setPlaceholderText("Enter quantity")
        self.qty_input.setStyleSheet("""
            QLineEdit {
                background-color: #F5F7FA;
                border: 2px solid #E0E6ED;
                border-radius: 10px;
                padding: 15px;
                font-size: 14px;
            }
            QLineEdit:focus {
                border: 2px solid #C62828;
                background-color: white;
            }
        """)
        form_layout.addWidget(self.qty_input)

        # Issue Date
        form_layout.addWidget(self.create_label("Issue Date"))
        self.date_input = QDateEdit()
        self.date_input.setDisplayFormat("dd-MM-yyyy")
        self.date_input.setDate(QDate.currentDate())
        self.date_input.setMaximumDate(QDate.currentDate())  # no issuing in the future
        self.date_input.setCalendarPopup(True)
        self.date_input.dateChanged.connect(self.update_balance_display)
        self.date_input.setStyleSheet("""
            QDateEdit {
                background-color: #F5F7FA;
                border: 2px solid #E0E6ED;
                border-radius: 10px;
                padding: 15px;
                font-size: 14px;
            }
            QDateEdit:focus {
                border: 2px solid #C62828;
                background-color: white;
            }
        """)
        form_layout.addWidget(self.date_input)

        # Issue button
        btn_issue = QPushButton("📤 Issue Stock")
        btn_issue.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_issue.setStyleSheet("""
            QPushButton {
                background-color: #C62828;
                color: white;
                border: none;
                border-radius: 10px;
                padding: 16px;
                font-size: 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #B71C1C;
            }
        """)
        btn_issue.clicked.connect(self.issue_stock)
        form_layout.addWidget(btn_issue)

        form_layout.addStretch()
        content_layout.addWidget(form_card, stretch=1)

        # Right Panel - Recent Issues
        list_card = self.create_card()
        list_layout = QVBoxLayout(list_card)
        list_layout.setContentsMargins(30, 30, 30, 30)
        list_layout.setSpacing(20)

        list_title = QLabel("Recent Issued Stock")
        list_title.setStyleSheet("font-size: 20px; font-weight: bold; color: #1A1A2E; background: transparent;")
        list_layout.addWidget(list_title)

        self.issue_list = QListWidget()
        self.issue_list.setStyleSheet("""
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
                background-color: #FFEBEE;
                color: #C62828;
            }
        """)
        list_layout.addWidget(self.issue_list)

        content_layout.addWidget(list_card, stretch=1)
        main_layout.addWidget(content, stretch=1)

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

    def style_combo(self, combo):
        combo.setStyleSheet("""
            QComboBox {
                background-color: #F5F7FA;
                border: 2px solid #E0E6ED;
                border-radius: 10px;
                padding: 15px;
                font-size: 14px;
            }
            QComboBox:focus {
                border: 2px solid #C62828;
            }
            QComboBox QAbstractItemView {
                background-color: white;
                border: 2px solid #E0E6ED;
                selection-background-color: #C62828;
                selection-color: white;
            }
        """)

    def load_items(self):
        self.item_dropdown.clear()
        items = self.item_service.get_all_items()
        for item in items:
            # Access by index for compatibility with packaged app
            item_id = item[0] if isinstance(item, (tuple, list)) else item["id"]
            item_name = item[1] if isinstance(item, (tuple, list)) else item["name"]
            self.item_dropdown.addItem(item_name, item_id)
        self.update_balance_display()

    def update_balance_display(self):
        item_id = self.item_dropdown.currentData()
        if not item_id:
            self.balance_label.setText("Available Balance: --")
            return
        balance = self.stock_service.get_stock_balance(item_id)
        text = f"Available Balance: {balance} units"
        selected = self.date_input.date()
        if selected != QDate.currentDate():
            on_date = self.stock_service.get_stock_balance(item_id, as_of=selected.toString("yyyy-MM-dd"))
            text += f"\n(on {selected.toString('dd-MM-yyyy')}: {on_date} units)"
        self.balance_label.setText(text)

    def issue_stock(self):
        item_id = self.item_dropdown.currentData()
        qty_text = self.qty_input.text().strip()

        if item_id is None:
            QMessageBox.warning(self, "Error", "Please select an item")
            return

        if not qty_text.isdigit() or int(qty_text) <= 0:
            QMessageBox.warning(self, "Error", "Enter a valid quantity")
            return

        qty = int(qty_text)
        issue_date = self.date_input.date().toString("yyyy-MM-dd")

        current_balance = self.stock_service.get_stock_balance(item_id)
        if qty > current_balance:
            QMessageBox.warning(self, "Error", f"Not enough stock! Available: {current_balance}")
            return

        # issue_stock also refuses a backdated issue for which stock hadn't arrived yet
        try:
            self.stock_service.issue_stock(item_id, qty, vendor_id=None, issue_date=issue_date)
        except StockError as e:
            QMessageBox.warning(self, "Cannot Issue", str(e))
            return
        QMessageBox.information(self, "Success", "Stock issued successfully for lab use!")
        self.qty_input.clear()
        self.update_balance_display()
        self.load_stock_issued()

    def load_stock_issued(self):
        self.issue_list.clear()
        for e in self.stock_service.get_recent_issues():
            self.issue_list.addItem(
                f"{e['date']} | {e['item_name']} | {e['issued_qty']} units issued (Lab Use)"
            )
