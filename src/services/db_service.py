"""
Database service module for Hospital Stock Management App.
Provides a singleton database connection so all parts of the app
use the same database and connection.

Writes can be grouped with `with db.transaction():` so that related changes
(e.g. a bill and its stock entry) are saved all-or-nothing.
"""
import logging
import sqlite3
from contextlib import contextmanager

from utils.db_path import get_database_path

log = logging.getLogger(__name__)

_db_instance = None


def get_db():
    """Get the singleton database instance."""
    global _db_instance
    if _db_instance is None:
        _db_instance = DatabaseService()
    return _db_instance


class DatabaseService:
    def __init__(self, db_path=None, connect=True):
        self.db_path = db_path or get_database_path()
        self.conn = None
        self._tx_depth = 0
        # Callbacks run after data changes are committed (used by the backup scheduler)
        self._change_listeners = []
        if connect:
            self.connect()

    def connect(self):
        """Create database connection with proper settings."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        # isolation_level=None: we control transactions explicitly with BEGIN/COMMIT
        self.conn = sqlite3.connect(str(self.db_path), isolation_level=None)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        # WAL journal: safer against power cuts and lets backups run while the app is open
        self.conn.execute("PRAGMA journal_mode = WAL")
        self.conn.execute("PRAGMA synchronous = NORMAL")

    def close(self):
        if self.conn:
            try:
                # Fold the WAL file back into the main .db file
                self.conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
            except sqlite3.Error:
                pass
            self.conn.close()
            self.conn = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    # ---- change notification -------------------------------------------------

    def add_change_listener(self, callback):
        self._change_listeners.append(callback)

    def _notify_change(self):
        for cb in list(self._change_listeners):
            try:
                cb()
            except Exception:
                log.exception("Change listener failed")

    # ---- transactions --------------------------------------------------------

    @contextmanager
    def transaction(self):
        """
        Group several writes into one all-or-nothing unit.
        Nested use is allowed; only the outermost block commits.
        """
        outermost = self._tx_depth == 0
        if outermost:
            self.conn.execute("BEGIN IMMEDIATE")
        self._tx_depth += 1
        try:
            yield self
        except BaseException:
            self._tx_depth -= 1
            if outermost:
                self.conn.execute("ROLLBACK")
            raise
        else:
            self._tx_depth -= 1
            if outermost:
                self.conn.execute("COMMIT")
                self._notify_change()

    # ---- queries -------------------------------------------------------------

    def execute(self, query, params=None):
        """Execute a write. Outside a transaction() block it is committed immediately."""
        if self._tx_depth > 0:
            cur = self.conn.execute(query, params or [])
            return cur.lastrowid
        with self.transaction():
            cur = self.conn.execute(query, params or [])
            return cur.lastrowid

    def fetch_all(self, query, params=None):
        """Fetch all rows as a list of dicts."""
        cur = self.conn.execute(query, params or [])
        return [dict(row) for row in cur.fetchall()]

    def fetch_one(self, query, params=None):
        """Fetch one row as a dict (or None)."""
        cur = self.conn.execute(query, params or [])
        row = cur.fetchone()
        return dict(row) if row else None

    def scalar(self, query, params=None):
        """Fetch the first column of the first row."""
        cur = self.conn.execute(query, params or [])
        row = cur.fetchone()
        return row[0] if row else None
