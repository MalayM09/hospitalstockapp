from PyQt6.QtWidgets import (
    QWidget, QLabel, QLineEdit, QPushButton,
    QVBoxLayout, QHBoxLayout, QMessageBox, QFrame, QSpacerItem, QSizePolicy
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QPixmap
from services.user_service import UserService
from ui.dashboard_window import DashboardWindow


class LoginWindow(QWidget):
    def __init__(self):
        super().__init__()

        self.user_service = UserService()
        self.setWindowTitle("Lab Stock Management System")
        self.setMinimumSize(1200, 800)
        
        # Set background gradient
        self.setStyleSheet("""
            QWidget#mainLogin {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #0D47A1, stop:0.5 #1565C0, stop:1 #1976D2);
            }
        """)
        self.setObjectName("mainLogin")

        self.init_ui()

    def init_ui(self):
        # Main layout
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # Left side - Branding
        left_widget = QWidget()
        left_widget.setStyleSheet("background: transparent;")
        left_layout = QVBoxLayout(left_widget)
        left_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Hospital icon/logo placeholder
        logo_label = QLabel("🏥")
        logo_label.setStyleSheet("font-size: 80px; background: transparent;")
        logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        left_layout.addWidget(logo_label)
        
        # Welcome text
        welcome_label = QLabel("Hospital Stock\nManagement System")
        welcome_label.setStyleSheet("""
            font-size: 36px;
            font-weight: bold;
            color: white;
            background: transparent;
        """)
        welcome_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        left_layout.addWidget(welcome_label)
        
        # Subtitle
        subtitle = QLabel("Health Center - MSU")
        subtitle.setStyleSheet("""
            font-size: 16px;
            color: rgba(255, 255, 255, 0.8);
            background: transparent;
            padding-top: 10px;
        """)
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        left_layout.addWidget(subtitle)
        
        main_layout.addWidget(left_widget, stretch=1)
        
        # Right side - Login Card
        right_widget = QWidget()
        right_widget.setFixedWidth(450)
        right_widget.setStyleSheet("""
            QWidget {
                background-color: white;
                border-top-left-radius: 30px;
                border-bottom-left-radius: 30px;
            }
        """)
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(50, 60, 50, 60)
        right_layout.setSpacing(20)
        
        # Login title
        login_title = QLabel("Welcome Back")
        login_title.setStyleSheet("""
            font-size: 32px;
            font-weight: bold;
            color: #1565C0;
            background: transparent;
        """)
        right_layout.addWidget(login_title)
        
        # Login subtitle
        login_subtitle = QLabel("Sign in to continue")
        login_subtitle.setStyleSheet("""
            font-size: 14px;
            color: #546E7A;
            background: transparent;
            margin-bottom: 30px;
        """)
        right_layout.addWidget(login_subtitle)
        
        # Username field
        username_label = QLabel("Username")
        username_label.setStyleSheet("""
            font-size: 14px;
            font-weight: 600;
            color: #1A1A2E;
            background: transparent;
        """)
        right_layout.addWidget(username_label)
        
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Enter your username")
        self.username_input.setStyleSheet("""
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
        right_layout.addWidget(self.username_input)
        
        # Password field
        password_label = QLabel("Password")
        password_label.setStyleSheet("""
            font-size: 14px;
            font-weight: 600;
            color: #1A1A2E;
            background: transparent;
            margin-top: 10px;
        """)
        right_layout.addWidget(password_label)
        
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Enter your password")
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.setStyleSheet("""
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
        right_layout.addWidget(self.password_input)
        
        # Spacer
        right_layout.addSpacing(20)
        
        # Login button
        login_button = QPushButton("Sign In")
        login_button.setCursor(Qt.CursorShape.PointingHandCursor)
        login_button.setStyleSheet("""
            QPushButton {
                background-color: #1565C0;
                color: white;
                border: none;
                border-radius: 10px;
                padding: 16px;
                font-size: 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #0D47A1;
            }
            QPushButton:pressed {
                background-color: #0D47A1;
            }
        """)
        login_button.clicked.connect(self.handle_login)
        right_layout.addWidget(login_button)
        
        # Connect enter key
        self.password_input.returnPressed.connect(self.handle_login)
        self.username_input.returnPressed.connect(lambda: self.password_input.setFocus())
        
        # Spacer to push content up
        right_layout.addStretch()
        
        # Footer
        footer = QLabel("© 2026 Lab Stock Management")
        footer.setStyleSheet("""
            font-size: 12px;
            color: #9E9E9E;
            background: transparent;
        """)
        footer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        right_layout.addWidget(footer)
        
        main_layout.addWidget(right_widget)

    def handle_login(self):
        username = self.username_input.text().strip()
        password = self.password_input.text().strip()

        if not username or not password:
            QMessageBox.warning(self, "Error", "Please enter username and password.")
            return

        if self.user_service.login(username, password):
            QMessageBox.information(self, "Success", "Login successful!")
            self.close()
            self.dashboard = DashboardWindow(username)
            self.dashboard.showMaximized()
        else:
            QMessageBox.critical(self, "Error", "Invalid credentials")
