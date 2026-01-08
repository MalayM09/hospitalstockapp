from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QListWidget, QMessageBox, QFrame, QScrollArea
)
from PyQt6.QtCore import Qt
from services.vendor_service import VendorService


class VendorWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.vendor_service = VendorService()

        self.setWindowTitle("Vendor Master")
        self.setMinimumSize(1200, 800)
        self.setStyleSheet("background-color: #F5F7FA;")

        self.init_ui()
        self.load_vendors()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Header
        header = self.create_header("📦", "Vendor Master", "Manage your vendor list")
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

        form_title = QLabel("Add / Edit Vendor")
        form_title.setStyleSheet("""
            font-size: 20px;
            font-weight: bold;
            color: #1A1A2E;
            background: transparent;
        """)
        form_layout.addWidget(form_title)

        # Vendor Name Input
        name_label = QLabel("Vendor Name")
        name_label.setStyleSheet("font-size: 14px; font-weight: 600; color: #1A1A2E; background: transparent;")
        form_layout.addWidget(name_label)

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Enter vendor name")
        self.name_input.setStyleSheet("""
            QLineEdit {
                background-color: #F5F7FA;
                border: 2px solid #E0E6ED;
                border-radius: 10px;
                padding: 15px;
                font-size: 14px;
            }
            QLineEdit:focus {
                border: 2px solid #1565C0;
                background-color: white;
            }
        """)
        form_layout.addWidget(self.name_input)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(15)

        add_btn = self.create_button("Add Vendor", "#1565C0", self.add_vendor)
        edit_btn = self.create_button("Update", "#00897B", self.edit_vendor)
        delete_btn = self.create_button("Delete", "#C62828", self.delete_vendor)

        btn_layout.addWidget(add_btn)
        btn_layout.addWidget(edit_btn)
        btn_layout.addWidget(delete_btn)
        form_layout.addLayout(btn_layout)

        form_layout.addStretch()
        content_layout.addWidget(form_card, stretch=1)

        # Right Panel - Vendor List
        list_card = self.create_card()
        list_layout = QVBoxLayout(list_card)
        list_layout.setContentsMargins(30, 30, 30, 30)
        list_layout.setSpacing(20)

        list_title = QLabel("Existing Vendors")
        list_title.setStyleSheet("""
            font-size: 20px;
            font-weight: bold;
            color: #1A1A2E;
            background: transparent;
        """)
        list_layout.addWidget(list_title)

        self.vendor_list = QListWidget()
        self.vendor_list.setStyleSheet("""
            QListWidget {
                background-color: #F5F7FA;
                border: 2px solid #E0E6ED;
                border-radius: 10px;
                padding: 10px;
                font-size: 14px;
            }
            QListWidget::item {
                padding: 15px;
                border-bottom: 1px solid #E0E6ED;
                border-radius: 8px;
            }
            QListWidget::item:selected {
                background-color: #E3F2FD;
                color: #1565C0;
            }
            QListWidget::item:hover {
                background-color: #ECEFF1;
            }
        """)
        self.vendor_list.itemClicked.connect(self.on_vendor_selected)
        list_layout.addWidget(self.vendor_list)

        content_layout.addWidget(list_card, stretch=2)
        main_layout.addWidget(content, stretch=1)

    def create_header(self, icon, title, subtitle):
        header = QFrame()
        header.setFixedHeight(100)
        header.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #0D47A1, stop:1 #1565C0);
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
        card.setStyleSheet("""
            QFrame {
                background-color: white;
                border-radius: 16px;
            }
        """)
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
                padding: 14px 24px;
                font-size: 14px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background-color: {color}DD;
            }}
        """)
        btn.clicked.connect(callback)
        return btn

    def on_vendor_selected(self, item):
        name = item.text().split(" - ", 1)[1] if " - " in item.text() else ""
        self.name_input.setText(name)

    def load_vendors(self):
        self.vendor_list.clear()
        vendors = self.vendor_service.get_all_vendors()
        for v in vendors:
            self.vendor_list.addItem(f"{v['id']} - {v['name']}")

    def add_vendor(self):
        name = self.name_input.text().strip()
        if not name:
            QMessageBox.warning(self, "Error", "Enter vendor name")
            return

        success = self.vendor_service.add_vendor(name)
        if success:
            self.load_vendors()
            self.name_input.clear()
            QMessageBox.information(self, "Success", "Vendor added successfully!")
        else:
            QMessageBox.warning(self, "Error", "Vendor already exists")

    def edit_vendor(self):
        selected = self.vendor_list.currentItem()
        if not selected:
            QMessageBox.warning(self, "Error", "Select a vendor")
            return

        vendor_id = int(selected.text().split(" - ")[0])
        name = self.name_input.text().strip()

        if not name:
            QMessageBox.warning(self, "Error", "Enter new vendor name")
            return

        success = self.vendor_service.update_vendor(vendor_id, name)
        if success:
            self.load_vendors()
            self.name_input.clear()
            QMessageBox.information(self, "Success", "Vendor updated successfully!")
        else:
            QMessageBox.warning(self, "Error", "Vendor name already exists")

    def delete_vendor(self):
        selected = self.vendor_list.currentItem()
        if not selected:
            QMessageBox.warning(self, "Error", "Select a vendor")
            return

        vendor_id = int(selected.text().split(" - ")[0])

        reply = QMessageBox.question(
            self, "Confirm Delete",
            "Are you sure you want to delete this vendor?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            success, error_msg = self.vendor_service.delete_vendor(vendor_id)
            if success:
                self.load_vendors()
                self.name_input.clear()
                QMessageBox.information(self, "Success", "Vendor deleted successfully!")
            else:
                QMessageBox.warning(self, "Cannot Delete", error_msg)

