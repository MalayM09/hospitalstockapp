"""
Database service module for Hospital Stock Management App.
Provides a singleton database connection to ensure all parts of the app
use the same database and connection.
"""
import sqlite3
from pathlib import Path
import sys

# Import centralized database path utility
from utils.db_path import get_database_path


# Singleton database connection
_db_instance = None


def get_db():
    """Get the singleton database instance."""
    global _db_instance
    if _db_instance is None:
        _db_instance = DatabaseService()
    return _db_instance


class DatabaseService:
    def __init__(self):
        self.db_path = get_database_path()
        self.conn = None
        self.backup_service = None
        self.connect()
        self._init_backup()
    
    def _init_backup(self):
        """Initialize backup service."""
        from services.backup_service import BackupService
        self.backup_service = BackupService(self.db_path)

    def connect(self):
        """Create database connection with proper settings."""
        # Ensure the directory exists
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        self.conn = sqlite3.connect(str(self.db_path))
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
                try:
                    self.backup_service.create_backup()
                except Exception:
                    pass  # Don't fail if backup fails
            
            return cur.lastrowid
        except sqlite3.Error as e:
            self.conn.rollback()
            raise e

    def fetch_all(self, query, params=None):
        """Fetch all rows and return as list of dictionaries."""
        cur = self.conn.cursor()
        cur.execute(query, params or [])
        rows = cur.fetchall()
        # Always convert to list of dicts for reliable access
        result = []
        for row in rows:
            if hasattr(row, 'keys'):
                result.append(dict(row))
            else:
                result.append(row)
        return result

    def fetch_one(self, query, params=None):
        """Fetch one row and return as dictionary."""
        cur = self.conn.cursor()
        cur.execute(query, params or [])
        row = cur.fetchone()
        # Always convert to dict for reliable access
        if row and hasattr(row, 'keys'):
            return dict(row)
        return row
