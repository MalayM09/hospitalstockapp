"""
Backup pieces shared by the Backup page and the startup restore dialog.
"""
import logging
import sys
from pathlib import Path

from PyQt6.QtCore import QProcess, Qt, pyqtSignal
from PyQt6.QtWidgets import QApplication, QDialog, QFileDialog, QHBoxLayout, QVBoxLayout, QWidget

from services.backup_service import inspect_database
from ui.theme import COLORS
from ui.widgets import DataTable, alert, button, confirm, label

log = logging.getLogger(__name__)


def restart_app():
    """Start a fresh copy of the app and quit this one."""
    if getattr(sys, "frozen", False):
        QProcess.startDetached(sys.executable, sys.argv[1:])
    else:
        QProcess.startDetached(sys.executable, sys.argv)
    QApplication.quit()


def human_size(n):
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.0f} {unit}"
        n /= 1024
    return f"{n:.1f} TB"


def describe_backup(path):
    info = inspect_database(path)
    if not info["ok"]:
        return False, f"Can't be used: {info['error']}"
    return True, (f"{info['items']} items · {info['vendors']} vendors · {info['bills']} purchase lines · "
                  f"{info['issues']} issues\nLatest purchase: {info['last_invoice'] or '—'}   ·   "
                  f"Latest issue: {info['last_issue'] or '—'}")


def confirm_and_restore(parent, service, path):
    """Ask, restore, and return True if restored (caller restarts or continues)."""
    ok, text = describe_backup(path)
    if not ok:
        alert(parent, "Cannot restore", text, "error")
        return False
    if not confirm(parent, "Restore this backup?",
                   f"All current data will be replaced with this backup:\n\n{text}\n\n"
                   "Your current data is backed up first, so this can be undone.",
                   ok_text="Restore", danger=True):
        return False
    QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
    try:
        service.restore(path)
    except Exception as e:
        log.exception("Restore failed")
        QApplication.restoreOverrideCursor()
        alert(parent, "Restore failed", f"The restore did not complete:\n\n{e}", "error")
        return False
    QApplication.restoreOverrideCursor()
    return True


class BackupList(QWidget):
    """All backups found, with a preview of the selected one."""
    selection_changed = pyqtSignal()

    def __init__(self, service):
        super().__init__()
        self.service = service
        self.backups = []
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(10)
        self.table = DataTable([("Date & time", "text"), ("Type", "text"), ("Location", "text"), ("Size", "text")],
                               stretch_col=2, empty_text="No backups found yet.")
        self.table.selection_changed.connect(self._preview)
        lay.addWidget(self.table, 1)
        self.preview = label("Select a backup to see what it contains.", wrap=True)
        self.preview.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.preview.setMinimumHeight(64)
        self._style_preview(None)
        lay.addWidget(self.preview)

    def _style_preview(self, ok):
        fg, bg = {None: (COLORS["muted"], COLORS["bg"]), True: (COLORS["text"], COLORS["accent_soft"]),
                  False: (COLORS["danger"], COLORS["danger_soft"])}[ok]
        self.preview.setStyleSheet(f"background:{bg}; color:{fg}; border-radius:8px; padding:10px 12px;")

    def refresh(self):
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            self.backups = self.service.list_backups()
        finally:
            QApplication.restoreOverrideCursor()
        self.table.set_rows([(b.time.strftime("%d %b %Y, %I:%M %p"), b.reason_label, b.location, human_size(b.size))
                             for b in self.backups], ids=list(range(len(self.backups))))
        self.preview.setVisible(bool(self.backups))
        if self.backups:
            self.table.view.selectRow(0)

    def selected(self):
        i = self.table.selected_id()
        return self.backups[i] if i is not None and i < len(self.backups) else None

    def _preview(self):
        b = self.selected()
        if b:
            ok, text = describe_backup(b.path)
            self.preview.setText(text)
            self.preview.setToolTip(str(b.path))
            self._style_preview(ok)
        self.selection_changed.emit()


class StartupRestoreDialog(QDialog):
    """
    Shown at startup when the database is missing (e.g. new computer after a
    disk failure) but backups exist somewhere, or when the database is damaged.
    """

    def __init__(self, service, title, message, parent=None):
        super().__init__(parent)
        self.service = service
        self.restored = False
        self.setWindowTitle(title)
        self.resize(860, 560)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(24, 22, 24, 20)
        lay.setSpacing(12)
        lay.addWidget(label(title, "pageTitle"))
        lay.addWidget(label(message, "muted", wrap=True))
        self.list = BackupList(service)
        lay.addWidget(self.list, 1)
        row = QHBoxLayout()
        row.addWidget(button("Restore selected", "primary", "arrow-counter-clockwise", callback=self.restore_selected))
        row.addWidget(button("Restore from file…", None, "folder-open", callback=self.restore_from_file))
        row.addStretch()
        row.addWidget(button("Continue without restoring", None, None, callback=self.reject))
        lay.addLayout(row)
        self.list.refresh()

    def _do_restore(self, path):
        if confirm_and_restore(self, self.service, path):
            self.restored = True
            self.accept()

    def restore_selected(self):
        b = self.list.selected()
        if b:
            self._do_restore(b.path)

    def restore_from_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "Choose a backup or recovered database file", "",
                                              "Database files (*.db *.sqlite *.sqlite3);;All files (*)")
        if path:
            self._do_restore(Path(path))
