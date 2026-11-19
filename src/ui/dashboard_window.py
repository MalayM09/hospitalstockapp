from PyQt6.QtWidgets import (
    QWidget, QPushButton, QVBoxLayout, QHBoxLayout, QLabel, 
    QFrame, QGridLayout, QSpacerItem, QSizePolicy
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

# Import screens
from ui.vendor_window import VendorWindow
from ui.item_window import ItemWindow
from ui.stock_issue_window import StockIssueWindow
from ui.bill_entry_window import BillEntryWindow
from ui.reports_window import ReportsWindow
from ui.stock_register_view_window import StockRegisterViewWindow
from ui.bill_details_view_window import BillDetailsViewWindow
from ui.stock_issuance_register_window import StockIssuanceRegisterWindow
from ui.backup_window import BackupWindow, style_banner


class DashboardWindow(QWidget):
    def __init__(self, username="Admin"):
        super().__init__()
        self.username = username
        self.setWindowTitle("Hospital Stock Management System - Dashboard")
        self.setMinimumSize(1200, 800)
        self.setStyleSheet("background-color: #F5F7FA;")

        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Top Header Bar
        header = QFrame()
        header.setFixedHeight(80)
        header.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #0D47A1, stop:1 #1565C0);
            }
        """)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(30, 0, 30, 0)

        # Logo and Title
        logo_label = QLabel("🏥")
        logo_label.setStyleSheet("font-size: 32px; background: transparent;")
        header_layout.addWidget(logo_label)

        title_label = QLabel("Hospital Stock Management")
        title_label.setStyleSheet("""
            font-size: 24px;
            font-weight: bold;
            color: white;
            background: transparent;
            padding-left: 10px;
        """)
        header_layout.addWidget(title_label)

        header_layout.addStretch()

        # User info
        user_label = QLabel(f"👤 {self.username}")
        user_label.setStyleSheet("""
            font-size: 16px;
            color: white;
            background: transparent;
            padding-right: 20px;
        """)
        header_layout.addWidget(user_label)

        # Logout button in header
        logout_btn = QPushButton("Logout")
        logout_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        logout_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 255, 255, 0.2);
                color: white;
                border: 2px solid rgba(255, 255, 255, 0.5);
                border-radius: 8px;
                padding: 10px 25px;
                font-size: 14px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.3);
                border-color: white;
            }
        """)
        logout_btn.clicked.connect(self.logout)
        header_layout.addWidget(logout_btn)

        main_layout.addWidget(header)

        # Content Area
        content = QWidget()
        content.setStyleSheet("background-color: #F5F7FA;")
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(40, 40, 40, 40)
        content_layout.setSpacing(30)

        # Welcome Section
        welcome_label = QLabel(f"Welcome back, {self.username}!")
        welcome_label.setStyleSheet("""
            font-size: 28px;
            font-weight: bold;
            color: #1A1A2E;
            background: transparent;
        """)
        content_layout.addWidget(welcome_label)

        subtitle = QLabel("What would you like to do today?")
        subtitle.setStyleSheet("""
            font-size: 16px;
            color: #546E7A;
            background: transparent;
            margin-bottom: 20px;
        """)
        content_layout.addWidget(subtitle)

        # Backup status - always visible so a missing off-site backup gets noticed
        self.backup_banner = QLabel()
        self.backup_banner.setCursor(Qt.CursorShape.PointingHandCursor)
        self.backup_banner.setToolTip("Click to open Backup & Restore")
        self.backup_banner.mousePressEvent = lambda event: self.open_backup_window()
        content_layout.addWidget(self.backup_banner)
        self.refresh_backup_banner()
        from services.backup_scheduler import get_scheduler
        scheduler = get_scheduler()
        if scheduler:
            scheduler.status_changed.connect(self.refresh_backup_banner)

        # Dashboard Cards Grid
        cards_grid = QGridLayout()
        cards_grid.setSpacing(20)

        # Define menu items with icons, colors, and descriptions
        menu_items = [
            ("📦", "Vendor Master", "Manage your vendors", "#1565C0", self.open_vendor_window),
            ("🏷️", "Item Master", "Manage inventory items", "#00897B", self.open_item_window),
            ("🛒", "Purchase Entry", "Record new purchases", "#7B1FA2", self.open_purchase_entry),
            ("📤", "Stock Issue", "Issue stock from inventory", "#C62828", self.open_stock_issue),
            ("📋", "Stock Register", "View stock register", "#00695C", self.open_stock_register_view),
            ("📑", "Issuance Register", "View stock issuance history", "#D32F2F", self.open_stock_issuance_register),
            ("📄", "Bill Details", "View all bill details", "#E65100", self.open_bill_details_view),
            ("📊", "Reports", "Generate reports", "#1976D2", self.open_reports),
            ("🛡️", "Backup & Restore", "Keep your data safe", "#37474F", self.open_backup_window),
        ]

        for i, (icon, title, desc, color, callback) in enumerate(menu_items):
            card = self.create_dashboard_card(icon, title, desc, color, callback)
            row = i // 4
            col = i % 4
            cards_grid.addWidget(card, row, col)

        content_layout.addLayout(cards_grid)
        content_layout.addStretch()

        main_layout.addWidget(content)

    def create_dashboard_card(self, icon, title, description, color, callback):
        """Create a styled dashboard card."""
        from PyQt6.QtWidgets import QFrame
        
        card = QFrame()
        card.setFixedSize(260, 160)
        card.setCursor(Qt.CursorShape.PointingHandCursor)
        card.setStyleSheet(f"""
            QFrame {{
                background-color: white;
                border: 2px solid transparent;
                border-radius: 16px;
            }}
            QFrame:hover {{
                background-color: #F8F9FA;
                border: 2px solid {color};
            }}
        """)
        
        # Store callback for click
        card.mousePressEvent = lambda event: callback()

        # Card layout
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(20, 20, 20, 20)
        card_layout.setSpacing(8)

        # Icon with colored background
        icon_label = QLabel(icon)
        icon_label.setStyleSheet(f"""
            font-size: 32px;
            background-color: {color}22;
            border-radius: 12px;
            padding: 8px;
            color: {color};
        """)
        icon_label.setFixedSize(56, 56)
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(icon_label)

        # Title
        title_label = QLabel(title)
        title_label.setStyleSheet("""
            font-size: 16px;
            font-weight: bold;
            color: #1A1A2E;
            background: transparent;
            padding-top: 5px;
        """)
        card_layout.addWidget(title_label)

        # Description
        desc_label = QLabel(description)
        desc_label.setStyleSheet("""
            font-size: 12px;
            color: #546E7A;
            background: transparent;
        """)
        card_layout.addWidget(desc_label)

        card_layout.addStretch()

        return card

    # Navigation functions
    def open_vendor_window(self):
        self.vendor_window = VendorWindow()
        self.vendor_window.showMaximized()

    def open_item_window(self):
        self.item_window = ItemWindow()
        self.item_window.showMaximized()

    def open_purchase_entry(self):
        self.purchase_window = BillEntryWindow()
        self.purchase_window.showMaximized()

    def open_stock_issue(self):
        self.stock_issue_window = StockIssueWindow()
        self.stock_issue_window.showMaximized()

    def open_reports(self):
        self.reports_window = ReportsWindow()
        self.reports_window.showMaximized()

    def open_stock_register_view(self):
        self.stock_register_view = StockRegisterViewWindow()
        self.stock_register_view.showMaximized()

    def open_bill_details_view(self):
        self.bill_details_view = BillDetailsViewWindow()
        self.bill_details_view.showMaximized()

    def open_stock_issuance_register(self):
        self.stock_issuance_register = StockIssuanceRegisterWindow()
        self.stock_issuance_register.showMaximized()

    def refresh_backup_banner(self):
        from services.backup_service import BackupService
        from services.db_service import get_db
        style_banner(self.backup_banner, BackupService(get_db()).status_summary())

    def open_backup_window(self):
        self.backup_window = BackupWindow()
        self.backup_window.showMaximized()

    def logout(self):
        self.close()
        from ui.login_window import LoginWindow
        self.login_window = LoginWindow()
        self.login_window.showMaximized()
