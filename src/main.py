import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PyQt6.QtWidgets import QApplication
from services.db_service import DatabaseService
from ui.login_window import LoginWindow


def ensure_db():
    """
    Ensure the database schema exists.
    This matches the schema defined in init_db.py (the source of truth).
    """
    db = DatabaseService()

    # Users table
    db.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL
    );
    """)

    # Vendors table
    db.execute("""
    CREATE TABLE IF NOT EXISTS vendors (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL
    );
    """)

    # Items table
    db.execute("""
    CREATE TABLE IF NOT EXISTS items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL
    );
    """)

    # Stock register (unified table for received and issued)
    db.execute("""
    CREATE TABLE IF NOT EXISTS stock_register (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        item_id INTEGER NOT NULL,
        vendor_id INTEGER,
        received_qty INTEGER DEFAULT 0,
        issued_qty INTEGER DEFAULT 0,
        balance_qty INTEGER DEFAULT 0,
        date TEXT,
        FOREIGN KEY (item_id) REFERENCES items(id),
        FOREIGN KEY (vendor_id) REFERENCES vendors(id)
    );
    """)

    # Bills table
    db.execute("""
    CREATE TABLE IF NOT EXISTS bills (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        item_id INTEGER,
        vendor_id INTEGER NOT NULL,
        invoice_number TEXT,
        invoice_date TEXT,
        batch_number TEXT,
        quantity INTEGER,
        amount REAL,
        cgst REAL,
        sgst REAL,
        round_off REAL,
        net_amount REAL,
        entry_date TEXT,
        FOREIGN KEY (item_id) REFERENCES items(id),
        FOREIGN KEY (vendor_id) REFERENCES vendors(id)
    );
    """)

    # Seed admin user if missing (with hashed password)
    user = db.fetch_one("SELECT * FROM users WHERE username = 'admin'")
    if not user:
        from services.user_service import UserService
        u = UserService()
        db.execute(
            "INSERT INTO users (username, password_hash) VALUES (?, ?)",
            ("admin", u.hash_password("admin"))
        )


def main():
    """Main entry point for the application."""
    # Ensure database exists
    ensure_db()
    
    # Start the PyQt6 application
    app = QApplication(sys.argv)
    
    # Apply professional theme
    from ui.theme import apply_theme
    apply_theme(app)
    
    # Show login window (fullscreen)
    login_window = LoginWindow()
    login_window.showMaximized()
    
    # Run the event loop
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
