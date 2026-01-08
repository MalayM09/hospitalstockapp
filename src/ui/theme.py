"""
Hospital Stock Management System - Professional Theme
Modern healthcare-inspired design with clean, professional styling
"""

# Color Palette - Healthcare/Medical Theme
COLORS = {
    'primary': '#1565C0',           # Deep Blue - main accent
    'primary_dark': '#0D47A1',      # Darker blue for hover states
    'primary_light': '#42A5F5',     # Light blue for highlights
    'secondary': '#00897B',         # Teal - secondary accent
    'success': '#2E7D32',           # Green for success states
    'warning': '#F57C00',           # Orange for warnings
    'danger': '#C62828',            # Red for errors/delete
    'background': '#F5F7FA',        # Light gray background
    'surface': '#FFFFFF',           # White surfaces
    'card': '#FFFFFF',              # Card backgrounds
    'text_primary': '#1A1A2E',      # Dark text
    'text_secondary': '#546E7A',    # Gray text
    'border': '#E0E6ED',            # Light borders
    'border_focus': '#1565C0',      # Focus border
    'header_bg': '#1565C0',         # Header background
    'sidebar_bg': '#0D47A1',        # Sidebar background
    'table_header': '#E3F2FD',      # Table header background
    'table_row_alt': '#FAFAFA',     # Alternate row background
}

# Main application stylesheet
MAIN_STYLE = f"""
    QMainWindow, QWidget {{
        background-color: {COLORS['background']};
        font-family: 'Segoe UI', 'SF Pro Display', -apple-system, sans-serif;
        font-size: 14px;
        color: {COLORS['text_primary']};
    }}
    
    QLabel {{
        color: {COLORS['text_primary']};
        font-size: 14px;
    }}
    
    QLabel[class="title"] {{
        font-size: 28px;
        font-weight: 600;
        color: {COLORS['primary']};
        padding: 10px 0;
    }}
    
    QLabel[class="subtitle"] {{
        font-size: 16px;
        color: {COLORS['text_secondary']};
        padding: 5px 0;
    }}
    
    QLabel[class="section-header"] {{
        font-size: 18px;
        font-weight: 600;
        color: {COLORS['text_primary']};
        padding: 15px 0 10px 0;
        border-bottom: 2px solid {COLORS['primary']};
    }}
    
    QLineEdit, QComboBox, QSpinBox, QDateEdit {{
        background-color: {COLORS['surface']};
        border: 2px solid {COLORS['border']};
        border-radius: 8px;
        padding: 12px 16px;
        font-size: 14px;
        color: {COLORS['text_primary']};
        min-height: 20px;
    }}
    
    QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDateEdit:focus {{
        border: 2px solid {COLORS['primary']};
        background-color: {COLORS['surface']};
    }}
    
    QLineEdit:read-only {{
        background-color: {COLORS['table_header']};
        color: {COLORS['text_secondary']};
    }}
    
    QLineEdit::placeholder {{
        color: {COLORS['text_secondary']};
    }}
    
    QComboBox::drop-down {{
        border: none;
        padding-right: 10px;
    }}
    
    QComboBox::down-arrow {{
        width: 12px;
        height: 12px;
    }}
    
    QComboBox QAbstractItemView {{
        background-color: {COLORS['surface']};
        border: 2px solid {COLORS['border']};
        border-radius: 8px;
        selection-background-color: {COLORS['primary']};
        selection-color: white;
        padding: 5px;
    }}
    
    QPushButton {{
        background-color: {COLORS['primary']};
        color: white;
        border: none;
        border-radius: 8px;
        padding: 12px 24px;
        font-size: 14px;
        font-weight: 600;
        min-height: 20px;
    }}
    
    QPushButton:hover {{
        background-color: {COLORS['primary_dark']};
    }}
    
    QPushButton:pressed {{
        background-color: {COLORS['primary_dark']};
    }}
    
    QPushButton:disabled {{
        background-color: {COLORS['border']};
        color: {COLORS['text_secondary']};
    }}
    
    QPushButton[class="secondary"] {{
        background-color: {COLORS['surface']};
        color: {COLORS['primary']};
        border: 2px solid {COLORS['primary']};
    }}
    
    QPushButton[class="secondary"]:hover {{
        background-color: {COLORS['table_header']};
    }}
    
    QPushButton[class="success"] {{
        background-color: {COLORS['success']};
    }}
    
    QPushButton[class="success"]:hover {{
        background-color: #1B5E20;
    }}
    
    QPushButton[class="danger"] {{
        background-color: {COLORS['danger']};
    }}
    
    QPushButton[class="danger"]:hover {{
        background-color: #B71C1C;
    }}
    
    QPushButton[class="warning"] {{
        background-color: {COLORS['warning']};
    }}
    
    QTableWidget {{
        background-color: {COLORS['surface']};
        border: 1px solid {COLORS['border']};
        border-radius: 8px;
        gridline-color: {COLORS['border']};
        font-size: 13px;
    }}
    
    QTableWidget::item {{
        padding: 12px;
        border-bottom: 1px solid {COLORS['border']};
    }}
    
    QTableWidget::item:selected {{
        background-color: {COLORS['table_header']};
        color: {COLORS['text_primary']};
    }}
    
    QHeaderView::section {{
        background-color: {COLORS['primary']};
        color: white;
        padding: 14px;
        font-weight: 600;
        font-size: 13px;
        border: none;
    }}
    
    QListWidget {{
        background-color: {COLORS['surface']};
        border: 2px solid {COLORS['border']};
        border-radius: 8px;
        padding: 5px;
        font-size: 14px;
    }}
    
    QListWidget::item {{
        padding: 12px;
        border-bottom: 1px solid {COLORS['border']};
        border-radius: 4px;
    }}
    
    QListWidget::item:selected {{
        background-color: {COLORS['table_header']};
        color: {COLORS['text_primary']};
    }}
    
    QListWidget::item:hover {{
        background-color: {COLORS['background']};
    }}
    
    QScrollBar:vertical {{
        background-color: {COLORS['background']};
        width: 12px;
        border-radius: 6px;
    }}
    
    QScrollBar::handle:vertical {{
        background-color: {COLORS['border']};
        border-radius: 6px;
        min-height: 30px;
    }}
    
    QScrollBar::handle:vertical:hover {{
        background-color: {COLORS['text_secondary']};
    }}
    
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        height: 0px;
    }}
    
    QMessageBox {{
        background-color: {COLORS['surface']};
    }}
    
    QMessageBox QLabel {{
        font-size: 14px;
        color: {COLORS['text_primary']};
    }}
    
    QMessageBox QPushButton {{
        min-width: 80px;
    }}
    
    QGroupBox {{
        background-color: {COLORS['surface']};
        border: 2px solid {COLORS['border']};
        border-radius: 12px;
        margin-top: 20px;
        padding-top: 15px;
        font-weight: 600;
    }}
    
    QGroupBox::title {{
        subcontrol-origin: margin;
        subcontrol-position: top left;
        padding: 5px 15px;
        background-color: {COLORS['primary']};
        color: white;
        border-radius: 6px;
    }}
"""

# Login window specific styles
LOGIN_STYLE = f"""
    QWidget#loginWidget {{
        background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
            stop:0 {COLORS['primary_dark']}, 
            stop:1 {COLORS['primary']});
    }}
    
    QWidget#loginCard {{
        background-color: {COLORS['surface']};
        border-radius: 20px;
    }}
"""

# Dashboard specific styles
DASHBOARD_STYLE = f"""
    QPushButton#dashboardBtn {{
        background-color: {COLORS['surface']};
        color: {COLORS['text_primary']};
        border: 2px solid {COLORS['border']};
        border-radius: 12px;
        padding: 20px;
        font-size: 16px;
        font-weight: 500;
        text-align: left;
    }}
    
    QPushButton#dashboardBtn:hover {{
        background-color: {COLORS['table_header']};
        border-color: {COLORS['primary']};
    }}
    
    QPushButton#logoutBtn {{
        background-color: {COLORS['danger']};
    }}
    
    QPushButton#logoutBtn:hover {{
        background-color: #B71C1C;
    }}
"""

def apply_theme(app):
    """Apply the global theme to the application."""
    app.setStyleSheet(MAIN_STYLE)
