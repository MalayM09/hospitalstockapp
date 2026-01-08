"""
Database path utilities for Hospital Stock Management App.
This module provides a centralized function to get the database path,
ensuring all parts of the application use the same database file.
"""
import sys
from pathlib import Path


def get_database_path():
    """
    Return the database path based on execution mode (dev vs packaged).
    
    For packaged executables (PyInstaller):
    - Windows: C:/Users/<username>/AppData/Local/HospitalStockApp/hospital.db
    - macOS: ~/Library/Application Support/HospitalStockApp/hospital.db
    
    For development mode:
    - Uses the 'data' folder in the project directory
    """
    if getattr(sys, 'frozen', False):  # PyInstaller bundled
        # Determine base directory based on platform
        if sys.platform == 'win32':
            base_dir = Path.home() / "AppData/Local/HospitalStockApp"
        elif sys.platform == 'darwin':
            base_dir = Path.home() / "Library/Application Support/HospitalStockApp"
        else:
            # Linux and other platforms
            base_dir = Path.home() / ".hospital_stock_app"
        
        # Create directory if it doesn't exist
        base_dir.mkdir(parents=True, exist_ok=True)
        return base_dir / "hospital.db"
    else:
        # Normal development mode - use data folder in project
        return Path(__file__).resolve().parents[2] / "data" / "hospital.db"


def ensure_data_directory():
    """Ensure the data directory exists."""
    db_path = get_database_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    return db_path
