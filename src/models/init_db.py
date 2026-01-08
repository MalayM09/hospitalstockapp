import sqlite3
from pathlib import Path
import sys


def get_db_path():
    """Return DB path based on execution mode (dev vs packaged)."""
    if getattr(sys, 'frozen', False):  # PyInstaller bundled
        base_dir = Path.home() / "Library/Application Support/HospitalStockApp"
        # For Windows, use AppData
        if sys.platform == 'win32':
            base_dir = Path.home() / "AppData/Local/HospitalStockApp"
        base_dir.mkdir(parents=True, exist_ok=True)
        return base_dir / "hospital.db"
    else:
        # normal development mode
        return Path(__file__).resolve().parents[2] / "data" / "hospital.db"


DB_PATH = get_db_path()

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("PRAGMA foreign_keys = ON;")

    # users
    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL
    );
    """)

    # vendors
    cur.execute("""
    CREATE TABLE IF NOT EXISTS vendors (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL
    );
    """)

    # items
    cur.execute("""
    CREATE TABLE IF NOT EXISTS items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL
    );
    """)

    # stock register
    cur.execute("""
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

    # bills
    cur.execute("""
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

    # Insert default admin user with hashed password
    import bcrypt
    hashed_password = bcrypt.hashpw('admin'.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    cur.execute(
        "INSERT OR IGNORE INTO users (id, username, password_hash) VALUES (?, ?, ?)",
        (1, 'admin', hashed_password)
    )

    conn.commit()
    conn.close()
    print(f"Database created at: {DB_PATH}")

if __name__ == "__main__":
    init_db()
