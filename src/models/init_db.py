"""
Command-line helper: create or upgrade the database without starting the GUI.

    python src/models/init_db.py

The schema itself lives in models/migrations.py (single source of truth).
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def init_db():
    from services.db_service import get_db
    from models.migrations import migrate
    from models.seed_data import ensure_admin_user, seed_if_first_run

    db = get_db()
    old, new = migrate(db.conn)
    ensure_admin_user(db)
    seed_if_first_run(db)
    print(f"Database at {db.db_path} is at schema v{new} (was v{old})")


if __name__ == "__main__":
    init_db()
