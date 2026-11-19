"""
Hospital Stock Management App - Main Entry Point

Startup sequence:
  1. Logging + crash handler (errors are logged and shown, not silent exits)
  2. If there is no database yet (e.g. a new computer after a disk failure)
     but backups exist on a pendrive / Google Drive folder -> offer to restore
  3. If the database is damaged -> offer to restore from a backup
  4. Back up before upgrading an older database, then apply migrations
  5. Create default admin user; seed default vendors/items on first run only
  6. Start the backup scheduler and show the sign-in screen
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
    from ui.backup_ui import StartupRestoreDialog

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


def _warn_if_no_offsite_backup(scheduler, parent):
    """At most once a day: a clear warning when no off-site backup exists."""
    from datetime import date
    from utils import settings
    summary = scheduler.service.status_summary()
    today = date.today().isoformat()
    if summary["level"] == "danger" and settings.get("offsite_warned_date") != today:
        settings.set("offsite_warned_date", today)
        QMessageBox.warning(parent, "Backup warning",
                            summary["text"] + "\n\nSet this up in Backup & Restore (left menu).")


class App:
    """Sign-in window <-> main window."""

    def __init__(self, scheduler):
        from ui.login_window import LoginWindow
        self.scheduler = scheduler
        self.main = None
        self.login = LoginWindow()
        self.login.logged_in.connect(self.on_login)

    def start(self):
        self.login.showMaximized()

    def on_login(self, username):
        from services.user_service import UserService
        from ui.main_window import MainWindow
        from ui.widgets import Toast
        self.main = MainWindow(username)
        self.main.logged_out.connect(self.on_logout)
        self.main.showMaximized()
        self.login.hide()
        _warn_if_no_offsite_backup(self.scheduler, self.main)
        if UserService().is_default_password(username):
            Toast(self.main, "You are using the default password — change it from the account menu "
                             "(bottom left).", "info", msec=7000)

    def on_logout(self):
        self.login.showMaximized()
        if self.main is not None:
            self.main.deleteLater()
            self.main = None


def main():
    setup_logging()
    install_exception_hook()

    app = QApplication(sys.argv)
    app.setApplicationName("HospitalStockApp")

    from ui.theme import apply_theme
    apply_theme(app)

    from utils.preview import apply_screen_simulation
    apply_screen_simulation()

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

    controller = App(scheduler)
    controller.start()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
