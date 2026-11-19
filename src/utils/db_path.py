"""
Path utilities for Hospital Stock Management App.

Everything the app stores on disk lives under one "app data" folder:

    <app data>/hospital.db        - the live database
    <app data>/backups/           - local backups (same disk - NOT enough on its own)
    <app data>/logs/              - error logs
    <app data>/settings.json      - backup destinations and other settings

Locations:
    Packaged (PyInstaller):
        Windows: C:/Users/<username>/AppData/Local/HospitalStockApp
        macOS:   ~/Library/Application Support/HospitalStockApp
        Linux:   ~/.hospital_stock_app
    Development: the 'data' folder in the project directory.

The environment variable HOSPITAL_STOCK_DATA_DIR overrides the location
(useful for testing against a throwaway copy).
"""
import os
import sys
from pathlib import Path


def get_app_data_dir() -> Path:
    override = os.environ.get("HOSPITAL_STOCK_DATA_DIR")
    if override:
        base_dir = Path(override)
    elif getattr(sys, 'frozen', False):  # PyInstaller bundled
        if sys.platform == 'win32':
            base_dir = Path.home() / "AppData/Local/HospitalStockApp"
        elif sys.platform == 'darwin':
            base_dir = Path.home() / "Library/Application Support/HospitalStockApp"
        else:
            base_dir = Path.home() / ".hospital_stock_app"
    else:
        base_dir = Path(__file__).resolve().parents[2] / "data"

    base_dir.mkdir(parents=True, exist_ok=True)
    return base_dir


def get_database_path() -> Path:
    return get_app_data_dir() / "hospital.db"


def get_local_backup_dir() -> Path:
    path = get_app_data_dir() / "backups"
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_log_dir() -> Path:
    path = get_app_data_dir() / "logs"
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_settings_path() -> Path:
    return get_app_data_dir() / "settings.json"


def ensure_data_directory():
    """Ensure the data directory exists."""
    return get_database_path()
