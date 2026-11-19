"""
Hospital Stock Management App - Main Entry Point

Startup sequence:
  1. Logging + crash handler (errors are logged and shown, not silent exits)
  2. If there is no database yet (e.g. a new computer after a disk failure)
     but backups exist on a pendrive / Google Drive folder -> offer to restore
  3. If the database is damaged -> offer to restore from a backup
  4. Back up before upgrading an older database, then apply migrations
  5. Create default admin user; seed default vendors/items on first run only
  6. Start the backup scheduler and show the login screen
"""
import logging
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PyQt6.QtWidgets import QApplication, QMessageBox

from utils.error_handling import install_exception_hook, setup_logging
from utils.db_path import get_database_path

log = logging.getLogger("main")


def _check_existing_database(app):
    """Steps 2-3. Returns normally to continue startup."""
    from services.backup_service import BackupService, check_integrity
    from services.db_service import get_db
    from ui.backup_window import StartupRestoreDialog

    db_path = get_database_path()
    is_new = not db_path.exists() or db_path.stat().st_size == 0

    if is_new:
        # Look for backups elsewhere before creating an empty database
        service = BackupService(get_db())
        if service.list_backups():
            dlg = StartupRestoreDialog(
                service,
                "Restore Your Data?",
                "There is no data on this computer yet, but backups were found "
                "(on a pendrive, backup folder or Google Drive / OneDrive).\n"
                "Choose the newest good backup and click Restore. "
                "Click 'Continue Without Restoring' only if you want to start fresh.",
            )
            dlg.exec()
        return

    ok, msg = check_integrity(db_path)
    if ok:
        return
    log.error("Database integrity check failed: %s", msg)
    import sqlite3
    import services.db_service as db_module
    try:
        db = get_db()
    except sqlite3.DatabaseError:
        # Too damaged to even open: restore works without a live connection
        db = db_module.DatabaseService(connect=False)
        db_module._db_instance = db
    service = BackupService(db)
    dlg = StartupRestoreDialog(
        service,
        "Database Problem Found",
        "The database file on this computer appears to be damaged "
        f"({msg[:200]}).\n\nRestoring the newest good backup is strongly recommended. "
        "The damaged file will be kept, not deleted.",
    )
    dlg.exec()


def _prepare_database():
    """Steps 4-5."""
    from models.migrations import LATEST_VERSION, get_version, migrate
    from models.seed_data import ensure_admin_user, seed_if_first_run
    from services.backup_service import BackupService
    from services.db_service import get_db

    db = get_db()
    if db.conn is None:  # damaged file and the user chose not to restore
        db.connect()
    version = get_version(db.conn)
    has_tables = db.scalar("SELECT COUNT(*) FROM sqlite_master WHERE type='table'") > 0
    if has_tables and version < LATEST_VERSION:
        try:
            BackupService(db).create_backup("premigrate")
        except Exception:
            log.exception("Pre-upgrade backup failed")
    migrate(db.conn)
    ensure_admin_user(db)
    seed_if_first_run(db)
    return db


def _warn_if_no_offsite_backup(scheduler):
    summary = scheduler.service.status_summary()
    if summary["level"] == "danger":
        QMessageBox.warning(
            None, "Backup Warning",
            summary["text"] + "\n\nYou can set this up from the dashboard: Backup & Restore.",
        )


def main():
    setup_logging()
    install_exception_hook()

    app = QApplication(sys.argv)
    app.setApplicationName("HospitalStockApp")

    from ui.theme import apply_theme
    apply_theme(app)

    try:
        _check_existing_database(app)
        db = _prepare_database()
    except Exception as e:
        log.exception("Startup failed")
        QMessageBox.critical(None, "Cannot Start",
                             f"The database could not be opened:\n\n{e}\n\n"
                             "Your backups have not been touched.")
        sys.exit(1)

    from services.backup_scheduler import BackupScheduler
    scheduler = BackupScheduler(db)
    scheduler.on_startup()

    def on_quit():
        try:
            scheduler.on_exit()
        finally:
            db.close()
            log.info("---- Application closed ----")

    app.aboutToQuit.connect(on_quit)

    from ui.login_window import LoginWindow
    login_window = LoginWindow()
    login_window.showMaximized()

    _warn_if_no_offsite_backup(scheduler)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
