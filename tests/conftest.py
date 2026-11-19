"""
Every test gets a brand-new, empty data folder (database, backups, settings),
so tests never touch real data and never affect each other.
"""
import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.fixture
def data_dir(tmp_path, monkeypatch):
    d = tmp_path / "data"
    d.mkdir()
    monkeypatch.setenv("HOSPITAL_STOCK_DATA_DIR", str(d))
    import services.db_service as dbs
    dbs._db_instance = None
    from utils import settings
    settings.set("backup_to_usb", False)
    yield d
    if dbs._db_instance is not None:
        dbs._db_instance.close()
    dbs._db_instance = None


@pytest.fixture
def db(data_dir):
    """Fresh, migrated, seeded database."""
    from models.migrations import migrate
    from models.seed_data import ensure_admin_user, seed_if_first_run
    from services.db_service import get_db
    d = get_db()
    migrate(d.conn)
    ensure_admin_user(d)
    seed_if_first_run(d)
    return d


@pytest.fixture
def ids(db):
    """Handy ids: a vendor and a few items."""
    item = lambda name: db.scalar("SELECT id FROM items WHERE name = ?", (name,))
    return {
        "vendor": db.scalar("SELECT id FROM vendors ORDER BY id LIMIT 1"),
        "vendor2": db.scalar("SELECT id FROM vendors ORDER BY id LIMIT 1 OFFSET 1"),
        "crp": item("CRP"), "glucose": item("Glucose Kit"), "hba1c": item("HBA1C"),
    }


@pytest.fixture(scope="session")
def qapp():
    from PyQt6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    return app
