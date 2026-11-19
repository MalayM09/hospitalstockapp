"""
Decides WHEN backups happen while the app is running:

  * after changes  - 5 minutes after the last change (so a burst of entries
                     makes one backup, not dozens)
  * daily          - once a day at/after the configured time, together with
                     the Excel exports (full data + last month's snapshot)
  * pendrive       - as soon as a USB pendrive is plugged in
  * app close      - if anything changed since the last backup

The old version copied the whole database after every single write; that was
slow, and its 10-file limit meant backups only reached back a few minutes.
"""
import logging
from datetime import date, datetime, timedelta

from PyQt6.QtCore import QObject, QTimer, pyqtSignal

from utils import settings
from services.backup_service import BackupService, detect_removable_drives

log = logging.getLogger(__name__)

AUTO_DELAY = timedelta(minutes=5)
CHECK_INTERVAL_MS = 60_000

_instance = None


def get_scheduler():
    return _instance


class BackupScheduler(QObject):
    # Emitted after every backup attempt and when data changes, so the
    # dashboard can refresh its status banner.
    status_changed = pyqtSignal()
    # Emitted after any committed data change (screens can refresh themselves)
    data_changed = pyqtSignal()

    def __init__(self, db, parent=None):
        super().__init__(parent)
        global _instance
        _instance = self
        self.db = db
        self.service = BackupService(db)
        self.dirty = False
        self.last_change = None
        self._known_drives = {str(d) for d in detect_removable_drives()}
        self._busy = False

        db.add_change_listener(self._on_change)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.tick)
        self.timer.start(CHECK_INTERVAL_MS)

    def _on_change(self):
        self.dirty = True
        self.last_change = datetime.now()
        self.data_changed.emit()

    def run_backup(self, reason, with_exports=False):
        """Run a backup now. Returns the result dict, or None if it failed."""
        if self._busy:
            return None
        self._busy = True
        try:
            result = self.service.create_backup(reason)
            self.dirty = False
            if with_exports:
                self._write_exports()
            return result
        except Exception:
            log.exception("Backup (%s) failed", reason)
            return None
        finally:
            self._busy = False
            self.status_changed.emit()

    def _write_exports(self):
        from services.export_service import write_exports_to_destination
        for d in self.service.destinations():
            try:
                if d.kind == "local" or d.root.exists():
                    write_exports_to_destination(d.folder)
            except Exception:
                log.exception("Excel export to %s failed", d.label)

    def _daily_due(self):
        today = date.today().isoformat()
        if settings.get("last_daily_backup_date") == today:
            return False
        try:
            hh, mm = (int(x) for x in (settings.get("daily_backup_time") or "13:00").split(":"))
        except ValueError:
            hh, mm = 13, 0
        return datetime.now() >= datetime.now().replace(hour=hh, minute=mm, second=0, microsecond=0)

    def run_daily(self):
        result = self.run_backup("daily", with_exports=True)
        if result and result["succeeded"]:
            settings.set("last_daily_backup_date", date.today().isoformat())
        return result

    def tick(self):
        try:
            # New pendrive plugged in?
            drives = {str(d) for d in detect_removable_drives()}
            new_drives = drives - self._known_drives
            self._known_drives = drives
            if new_drives and settings.get("backup_to_usb"):
                log.info("Pendrive detected: %s", ", ".join(sorted(new_drives)))
                self.run_backup("usb", with_exports=True)
                return

            if self._daily_due():
                self.run_daily()
                return

            if self.dirty and self.last_change and datetime.now() - self.last_change >= AUTO_DELAY:
                self.run_backup("auto")
        except Exception:
            log.exception("Backup scheduler tick failed")

    def on_startup(self):
        """Backup at launch if none was made today; catch up a missed daily backup."""
        if self._daily_due():
            self.run_daily()
        else:
            last = settings.get("last_backup_time")
            if not last or not last.startswith(date.today().isoformat()):
                self.run_backup("startup")

    def on_exit(self):
        self.timer.stop()
        if self.dirty:
            self.run_backup("exit")
