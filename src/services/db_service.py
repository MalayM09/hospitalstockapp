import sqlite3
from pathlib import Path
import sys


def app_data_path():
    """Return DB path based on execution mode (dev vs packaged)."""
    if getattr(sys, 'frozen', False):  # PyInstaller bundled
        base_dir = Path.home() / "Library/Application Support/HospitalStockApp"
        base_dir.mkdir(parents=True, exist_ok=True)
        return base_dir / "hospital.db"
    else:
        # normal development mode
        return Path(__file__).resolve().parents[2] / "data" / "hospital.db"


class DatabaseService:
    def __init__(self):
        self.db_path = app_data_path()
        self.conn = None
        self.backup_service = None
        self.connect()
        self._init_backup()
    
    def _init_backup(self):
        """Initialize backup service."""
        from services.backup_service import BackupService
        self.backup_service = BackupService(self.db_path)

    def connect(self):
        self.conn = sqlite3.connect(self.db_path)
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.conn.row_factory = sqlite3.Row

    def close(self):
        """Close the database connection."""
        if self.conn:
            self.conn.close()
            self.conn = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def execute(self, query, params=None):
        """Execute a query with error handling, rollback on failure, and auto-backup."""
        try:
            cur = self.conn.cursor()
            cur.execute(query, params or [])
            self.conn.commit()
            
            # Auto-backup after successful write operations
            if self.backup_service and query.strip().upper().startswith(('INSERT', 'UPDATE', 'DELETE')):
                self.backup_service.create_backup()
            
            return cur.lastrowid
        except sqlite3.Error as e:
            self.conn.rollback()
            raise e

    def fetch_all(self, query, params=None):
        cur = self.conn.cursor()
        cur.execute(query, params or [])
        return cur.fetchall()

    def fetch_one(self, query, params=None):
        cur = self.conn.cursor()
        cur.execute(query, params or [])
        return cur.fetchone()
