from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QListWidget, QMessageBox, QFrame
)
from PyQt6.QtCore import Qt
from services.item_service import ItemService


class ItemWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.item_service = ItemService()

        self.setWindowTitle("Item Master")
        self.setMinimumSize(1200, 800)
        self.setStyleSheet("background-color: #F5F7FA;")

        self.init_ui()
        self.load_items()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Header
        header = self.create_header("🏷️", "Item Master", "Manage your inventory items")
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

        form_title = QLabel("Add / Edit Item")
        form_title.setStyleSheet("""
            font-size: 20px;
            font-weight: bold;
            color: #1A1A2E;
            background: transparent;
        """)
        form_layout.addWidget(form_title)

        # Item Name Input
        name_label = QLabel("Item Name")
        name_label.setStyleSheet("font-size: 14px; font-weight: 600; color: #1A1A2E; background: transparent;")
        form_layout.addWidget(name_label)

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Enter item name")
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

        add_btn = self.create_button("Add Item", "#00897B", self.add_item)
        edit_btn = self.create_button("Update", "#1565C0", self.edit_item)
        delete_btn = self.create_button("Delete", "#C62828", self.delete_item)

        btn_layout.addWidget(add_btn)
        btn_layout.addWidget(edit_btn)
        btn_layout.addWidget(delete_btn)
        form_layout.addLayout(btn_layout)

        form_layout.addStretch()
        content_layout.addWidget(form_card, stretch=1)

        # Right Panel - Item List
        list_card = self.create_card()
        list_layout = QVBoxLayout(list_card)
        list_layout.setContentsMargins(30, 30, 30, 30)
        list_layout.setSpacing(20)

        list_title = QLabel("Existing Items")
        list_title.setStyleSheet("""
            font-size: 20px;
            font-weight: bold;
            color: #1A1A2E;
            background: transparent;
        """)
        list_layout.addWidget(list_title)

        self.item_list = QListWidget()
        self.item_list.setStyleSheet("""
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
                background-color: #E0F2F1;
                color: #00897B;
            }
            QListWidget::item:hover {
                background-color: #ECEFF1;
            }
        """)
        self.item_list.itemClicked.connect(self.on_item_selected)
        list_layout.addWidget(self.item_list)

        content_layout.addWidget(list_card, stretch=2)
        main_layout.addWidget(content, stretch=1)

    def create_header(self, icon, title, subtitle):
        header = QFrame()
        header.setFixedHeight(100)
        header.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #00695C, stop:1 #00897B);
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

    def on_item_selected(self, item):
        name = item.text().split(" - ", 1)[1] if " - " in item.text() else ""
        self.name_input.setText(name)

    def load_items(self):
        self.item_list.clear()
        items = self.item_service.get_all_items()
        for i in items:
            # Access by index for compatibility with packaged app
            item_id = i[0] if isinstance(i, (tuple, list)) else i['id']
            item_name = i[1] if isinstance(i, (tuple, list)) else i['name']
            self.item_list.addItem(f"{item_id} - {item_name}")


    def add_item(self):
        name = self.name_input.text().strip()
        if not name:
            QMessageBox.warning(self, "Error", "Enter item name")
            return

        success = self.item_service.add_item(name)
        if success:
            self.load_items()
            self.name_input.clear()
            QMessageBox.information(self, "Success", "Item added successfully!")
        else:
            QMessageBox.warning(self, "Error", "Item already exists")

    def edit_item(self):
        selected = self.item_list.currentItem()
        if not selected:
            QMessageBox.warning(self, "Error", "Select an item")
            return

        item_id = int(selected.text().split(" - ")[0])
        name = self.name_input.text().strip()

        if not name:
            QMessageBox.warning(self, "Error", "Enter new name")
            return

        success = self.item_service.update_item(item_id, name)
        if success:
            self.load_items()
            self.name_input.clear()
            QMessageBox.information(self, "Success", "Item updated successfully!")
        else:
            QMessageBox.warning(self, "Error", "Item name already exists")

    def delete_item(self):
        selected = self.item_list.currentItem()
        if not selected:
            QMessageBox.warning(self, "Error", "Select an item")
            return

        item_id = int(selected.text().split(" - ")[0])

        reply = QMessageBox.question(
            self, "Confirm Delete", "Are you sure?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            success, error_msg = self.item_service.delete_item(item_id)
            if success:
                self.load_items()
                self.name_input.clear()
                QMessageBox.information(self, "Success", "Item deleted successfully!")
            else:
                QMessageBox.warning(self, "Cannot Delete", error_msg)

