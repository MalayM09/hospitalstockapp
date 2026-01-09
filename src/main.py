"""
Hospital Stock Management App - Main Entry Point
"""
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PyQt6.QtWidgets import QApplication
from services.db_service import get_db
from ui.login_window import LoginWindow


def ensure_db():
    """
    Ensure the database and all tables exist.
    Uses the singleton database instance for consistency.
    """
    db = get_db()

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
        expiry_date TEXT,
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


def seed_initial_data():
    """
    Seed initial vendors, items, and stock into the database.
    Uses the singleton database instance for consistency.
    """
    from datetime import datetime
    
    db = get_db()
    
    # Vendor list
    vendors = [
        "SEEMA CHEMICALS", "RIDDHI TRADERS", "ADI ENTERPRISE",
        "PRASAD SURGICAL", "KRISHNA ENTERPRISE", "CURE SUPPLIERS",
        "AN PHARMA", "GTB ENTERPRISE", "J&B MEDICAL AND SURGICAL",
        "RBM DISRIBUTOR", "MATRIX BIOMEDICAL", "JP ENTERPRISE", "PRAKHAR ENTERPRISE"
    ]
    
    # Items with initial stock quantities
    items_with_qty = {
        "Glucose Kit": 0, "Serum cholesterol": 0, "Serum triglyceride": 0,
        "Blood urea": 0, "Serum creatinine": 0, "atotal bilirubin": 0,
        "Serum SGPT": 0, "Serum Alkaline phosphate": 0, "Serum uric acid": 0,
        "HBA1C": 0, "CRP Kit": 0, "RA": 2, "Serum widal": 1,
        "Pregnancy test": 50, "M.T. test": 0, "Urine strick": 5,
        "Blood group": 0, "Cell pack (diluent foe 3-part)": 0,
        "Dengue card": 30, "Cell clean": 0, "Vaccurate k3. E.D.T.A.": 500,
        "Vaccurate k3. Plain": 600, "Vaccurate k3. FLUORIDE": 300,
        "Giemasa stain": 2, "Printer Roll": 4,
        "Stromatolyser (lyse solution for 3 part)": 0, "Distilled water": 4,
        "Micro slide": 2, "Cover slip": 4, "Filter paper": 1,
        "PM KIT(ERBA EM DESTINY 180)": 0, "Paper tape": 0,
        "Yellow tips": 0, "Blue tips": 0, "ESR tube": 0,
        "Tissue paper roll": 3, "Cleaner wood oil": 2, "Turniket belt": 3,
        "Fouchets reagent": 0, "Barium Chloride": 0, "Malaria card": 50,
        "Urine container beaker": 30, "ROTER": 3, "XL AUTO WASH": 1,
        "XL MULTICA ERBA NORM": 0, "Blood collection needle 22g": 4,
        "Collection vial 1.5 ml": 0, "URBA Path": 0, "URBA XL MULITCAL": 0, "CRP": 0
    }
    
    # Insert vendors
    for vendor in vendors:
        try:
            db.execute("INSERT OR IGNORE INTO vendors (name) VALUES (?)", (vendor,))
        except Exception:
            pass
    
    # Insert items
    for item_name in items_with_qty.keys():
        try:
            db.execute("INSERT OR IGNORE INTO items (name) VALUES (?)", (item_name,))
        except Exception:
            pass
    
    # Add initial stock for items with quantity > 0
    today = datetime.now().strftime("%Y-%m-%d")
    for item_name, quantity in items_with_qty.items():
        if quantity > 0:
            result = db.fetch_one("SELECT id FROM items WHERE name = ?", (item_name,))
            if result:
                item_id = result['id']
                existing = db.fetch_one("SELECT id FROM stock_register WHERE item_id = ?", (item_id,))
                if not existing:
                    try:
                        db.execute("""
                            INSERT INTO stock_register (item_id, vendor_id, received_qty, issued_qty, balance_qty, date)
                            VALUES (?, NULL, ?, 0, ?, ?)
                        """, (item_id, quantity, quantity, today))
                    except Exception:
                        pass
    
    print("✅ Database initialized with vendors, items & stock.")


def main():
    """Main entry point for the application."""
    # Ensure database and tables exist
    ensure_db()
    
    # Seed initial data
    seed_initial_data()
    
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
