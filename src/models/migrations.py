"""
Database schema and migrations.

The schema version is stored in SQLite's `PRAGMA user_version`. Each migration
upgrades the database by exactly one version and runs inside a transaction, so
a failed upgrade leaves the database untouched. Old databases (including old
backups being restored) are upgraded automatically when opened.

To change the schema later: add a new function to MIGRATIONS. Never edit an
existing migration once it has shipped.
"""
import logging

log = logging.getLogger(__name__)


def _columns(conn, table):
    return {row[1] for row in conn.execute(f"PRAGMA table_info({table})")}


def _add_column(conn, table, column_def):
    name = column_def.split()[0]
    if name not in _columns(conn, table):
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column_def}")


def migration_1_baseline(conn):
    """The original schema (as shipped up to 2026). Safe on existing databases."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL
        )""")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS vendors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL
        )""")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL
        )""")
    conn.execute("""
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
        )""")
    conn.execute("""
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
        )""")
    # Some very old databases were created without expiry_date
    _add_column(conn, "bills", "expiry_date TEXT")


def migration_2_integrity(conn):
    """
    - stock rows get a type (OPENING / PURCHASE / ISSUE / ADJUSTMENT), a remarks
      field, and a link to the bill that created them, so editing a bill updates
      its stock row instead of piling up correction rows
    - bills store their GST rate and IGST so they can be re-calculated on edit
    - app_meta table (first-run flags etc.)
    - indexes for faster lookups
    """
    _add_column(conn, "stock_register", "txn_type TEXT")
    _add_column(conn, "stock_register", "bill_id INTEGER REFERENCES bills(id)")
    _add_column(conn, "stock_register", "remarks TEXT")
    _add_column(conn, "stock_register", "created_at TEXT")

    _add_column(conn, "bills", "gst_rate REAL")
    _add_column(conn, "bills", "igst REAL DEFAULT 0")
    _add_column(conn, "bills", "created_at TEXT")
    _add_column(conn, "bills", "updated_at TEXT")

    conn.execute("""
        CREATE TABLE IF NOT EXISTS app_meta (
            key TEXT PRIMARY KEY,
            value TEXT
        )""")

    # --- Backfill transaction types for existing rows
    conn.execute("UPDATE stock_register SET txn_type = 'ISSUE' WHERE txn_type IS NULL AND issued_qty > 0")
    conn.execute("""UPDATE stock_register SET txn_type = 'ADJUSTMENT'
                    WHERE txn_type IS NULL AND received_qty < 0""")
    conn.execute("""UPDATE stock_register SET txn_type = 'OPENING'
                    WHERE txn_type IS NULL AND vendor_id IS NULL AND received_qty > 0""")
    conn.execute("UPDATE stock_register SET txn_type = 'PURCHASE' WHERE txn_type IS NULL")

    # --- Link existing bills to the stock row they created.
    # The old code inserted the stock row with the same item, vendor, quantity
    # and date (= entry_date) as the bill, so an exact match identifies it.
    bills = conn.execute("""
        SELECT id, item_id, vendor_id, quantity, entry_date FROM bills
        WHERE item_id IS NOT NULL AND quantity > 0 ORDER BY id
    """).fetchall()
    linked = 0
    for bill_id, item_id, vendor_id, qty, entry_date in bills:
        row = conn.execute("""
            SELECT id FROM stock_register
            WHERE bill_id IS NULL AND txn_type = 'PURCHASE'
              AND item_id = ? AND vendor_id IS ? AND received_qty = ? AND date IS ?
            ORDER BY id LIMIT 1
        """, (item_id, vendor_id, qty, entry_date)).fetchone()
        if row:
            conn.execute("UPDATE stock_register SET bill_id = ? WHERE id = ?", (bill_id, row[0]))
            linked += 1
    if bills:
        log.info("Migration 2: linked %d of %d existing bills to their stock rows", linked, len(bills))

    # --- Backfill GST rate from stored tax amounts
    conn.execute("""
        UPDATE bills
        SET gst_rate = ROUND((COALESCE(cgst, 0) + COALESCE(sgst, 0)) * 100.0 / amount, 2)
        WHERE gst_rate IS NULL AND amount > 0
    """)
    conn.execute("UPDATE bills SET gst_rate = 0 WHERE gst_rate IS NULL")
    conn.execute("UPDATE bills SET igst = 0 WHERE igst IS NULL")

    # --- Existing databases have already been seeded with the default lists
    has_items = conn.execute("SELECT EXISTS(SELECT 1 FROM items)").fetchone()[0]
    if has_items:
        conn.execute("INSERT OR IGNORE INTO app_meta (key, value) VALUES ('seeded', '1')")

    conn.execute("CREATE INDEX IF NOT EXISTS idx_stock_item_date ON stock_register(item_id, date)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_stock_bill ON stock_register(bill_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_bills_invoice_date ON bills(invoice_date)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_bills_vendor ON bills(vendor_id)")


MIGRATIONS = [
    migration_1_baseline,
    migration_2_integrity,
]

LATEST_VERSION = len(MIGRATIONS)


def get_version(conn):
    return conn.execute("PRAGMA user_version").fetchone()[0]


def migrate(conn):
    """
    Bring the database up to LATEST_VERSION.
    `conn` must be a sqlite3 connection with isolation_level=None.
    Returns (old_version, new_version).
    """
    old = get_version(conn)
    if old > LATEST_VERSION:
        raise RuntimeError(
            f"This database was created by a newer version of the app "
            f"(schema v{old}; this app supports up to v{LATEST_VERSION}). "
            f"Please update the app."
        )
    for version in range(old + 1, LATEST_VERSION + 1):
        log.info("Applying database migration %d", version)
        conn.execute("BEGIN IMMEDIATE")
        try:
            MIGRATIONS[version - 1](conn)
            conn.execute(f"PRAGMA user_version = {version}")
            conn.execute("COMMIT")
        except Exception:
            conn.execute("ROLLBACK")
            log.exception("Migration %d failed - database left at version %d", version, version - 1)
            raise
    return old, LATEST_VERSION
