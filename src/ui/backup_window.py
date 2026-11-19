"""
Backup & Restore screen, and the startup restore dialog.
"""
import logging
import sys
from datetime import date
from pathlib import Path

from PyQt6.QtCore import QDate, QProcess, Qt, QTime, pyqtSignal
from PyQt6.QtWidgets import (
    QAbstractItemView, QApplication, QCheckBox, QDateEdit, QDialog, QFileDialog, QFrame,
    QHBoxLayout, QHeaderView, QLabel, QListWidget, QListWidgetItem, QMessageBox, QPushButton,
    QTableWidget, QTableWidgetItem, QTimeEdit, QVBoxLayout, QWidget,
)

from services.backup_service import (
    BackupService, detect_cloud_folders, inspect_database,
)
from services.db_service import get_db
from utils import settings

log = logging.getLogger(__name__)

ACCENT = "#37474F"

BANNER_COLORS = {
    "ok": ("#E8F5E9", "#2E7D32", "✅"),
    "warn": ("#FFF8E1", "#E65100", "⚠️"),
    "danger": ("#FFEBEE", "#C62828", "⚠️"),
}


def style_banner(label, summary):
    bg, fg, icon = BANNER_COLORS[summary["level"]]
    label.setText(f"{icon}  {summary['text']}")
    label.setWordWrap(True)
    label.setStyleSheet(f"""
        background-color: {bg}; color: {fg}; border: 1px solid {fg};
        border-radius: 10px; padding: 12px 16px; font-size: 14px; font-weight: 600;
    """)


def restart_app():
    """Start a fresh copy of the app and quit this one."""
    if getattr(sys, "frozen", False):
        QProcess.startDetached(sys.executable, sys.argv[1:])
    else:
        QProcess.startDetached(sys.executable, sys.argv)
    QApplication.quit()


def _human_size(n):
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.0f} {unit}"
        n /= 1024
    return f"{n:.1f} TB"


def _button(text, color, callback, outline=False):
    btn = QPushButton(text)
    btn.setCursor(Qt.CursorShape.PointingHandCursor)
    if outline:
        css = f"""
            QPushButton {{ background-color: white; color: {color}; border: 2px solid {color};
                           border-radius: 10px; padding: 10px 18px; font-size: 13px; font-weight: 600; }}
            QPushButton:hover {{ background-color: {color}; color: white; }}
        """
    else:
        css = f"""
            QPushButton {{ background-color: {color}; color: white; border: none;
                           border-radius: 10px; padding: 12px 20px; font-size: 14px; font-weight: 600; }}
            QPushButton:hover {{ background-color: {color}DD; }}
        """
    btn.setStyleSheet(css)
    btn.clicked.connect(callback)
    return btn


def _section_title(text):
    label = QLabel(text)
    label.setStyleSheet("font-size: 18px; font-weight: bold; color: #1A1A2E; background: transparent;")
    return label


def _card():
    card = QFrame()
    card.setStyleSheet("QFrame { background-color: white; border-radius: 16px; }")
    return card


class BackupListWidget(QWidget):
    """Table of every backup found, with a preview of the selected one."""

    selection_changed = pyqtSignal()

    def __init__(self, service, parent=None):
        super().__init__(parent)
        self.service = service
        self.backups = []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Date & Time", "Type", "Location", "Size"])
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        hv = self.table.horizontalHeader()
        hv.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        hv.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.table.setStyleSheet(f"""
            QTableWidget {{ background-color: white; border: 1px solid #E0E6ED; border-radius: 8px;
                            font-size: 13px; alternate-background-color: #FAFAFA; }}
            QTableWidget::item {{ padding: 8px; }}
            QTableWidget::item:selected {{ background-color: #ECEFF1; color: #1A1A2E; }}
            QHeaderView::section {{ background-color: {ACCENT}; color: white; padding: 10px;
                                    font-weight: bold; border: none; }}
        """)
        self.table.itemSelectionChanged.connect(self._on_select)
        layout.addWidget(self.table, stretch=1)

        self.preview = QLabel("Select a backup to see what it contains.")
        self.preview.setWordWrap(True)
        self.preview.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.preview.setStyleSheet("""
            background-color: #F5F7FA; border: 1px solid #E0E6ED; border-radius: 10px;
            padding: 12px; font-size: 13px; color: #1A1A2E;
        """)
        self.preview.setMinimumHeight(90)
        layout.addWidget(self.preview)

    def refresh(self):
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            self.backups = self.service.list_backups()
        finally:
            QApplication.restoreOverrideCursor()
        self.table.setRowCount(len(self.backups))
        for row, b in enumerate(self.backups):
            values = [b.time.strftime("%d %b %Y  %H:%M"), b.reason_label, b.location, _human_size(b.size)]
            for col, v in enumerate(values):
                item = QTableWidgetItem(v)
                item.setToolTip(str(b.path))
                self.table.setItem(row, col, item)
        if self.backups:
            self.table.selectRow(0)
        else:
            self.preview.setText("No backups found yet.")

    def selected(self):
        row = self.table.currentRow()
        if 0 <= row < len(self.backups):
            return self.backups[row]
        return None

    def _on_select(self):
        b = self.selected()
        if b:
            self.preview.setText(describe_backup(b.path))
        self.selection_changed.emit()


def describe_backup(path):
    info = inspect_database(path)
    if not info["ok"]:
        return f"❌  {info['error']}\n{path}"
    return (
        f"✅  Good backup — {info['items']} items, {info['vendors']} vendors, "
        f"{info['bills']} purchase bills, {info['issues']} issue entries.\n"
        f"Latest purchase: {info['last_invoice'] or '—'}    ·    "
        f"Latest issue: {info['last_issue'] or '—'}\n"
        f"File: {path}"
    )


def confirm_and_restore(parent, service, path):
    """Ask, restore, then restart. Returns True if restored."""
    info = inspect_database(path)
    if not info["ok"]:
        QMessageBox.critical(parent, "Cannot Restore", f"This file can't be restored:\n\n{info['error']}")
        return False
    reply = QMessageBox.question(
        parent, "Restore Backup",
        "Replace ALL current data with this backup?\n\n"
        f"{describe_backup(path)}\n\n"
        "Your current data will be backed up first, so this can be undone.\n"
        "The app will restart afterwards.",
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        QMessageBox.StandardButton.No,
    )
    if reply != QMessageBox.StandardButton.Yes:
        return False
    QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
    try:
        service.restore(path)
    except Exception as e:
        QApplication.restoreOverrideCursor()
        log.exception("Restore failed")
        QMessageBox.critical(parent, "Restore Failed", f"The restore did not complete:\n\n{e}")
        return False
    QApplication.restoreOverrideCursor()
    QMessageBox.information(parent, "Restored", "Backup restored successfully. The app will now restart.")
    return True


class BackupWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Backup & Restore")
        self.setMinimumSize(1100, 750)
        self.setStyleSheet("background-color: #F5F7FA;")
        self.service = BackupService(get_db())
        self.init_ui()
        self.load_destinations()
        self.backup_list.refresh()

        from services.backup_scheduler import get_scheduler
        sched = get_scheduler()
        if sched:
            sched.status_changed.connect(self.refresh_status)

    # ---- layout -------------------------------------------------------------

    def init_ui(self):
        main = QVBoxLayout(self)
        main.setContentsMargins(0, 0, 0, 0)
        main.setSpacing(0)
        main.addWidget(self.create_header())

        content = QWidget()
        content.setStyleSheet("background-color: #F5F7FA;")
        outer = QVBoxLayout(content)
        outer.setContentsMargins(30, 20, 30, 30)
        outer.setSpacing(16)

        self.banner = QLabel()
        outer.addWidget(self.banner)

        cols = QHBoxLayout()
        cols.setSpacing(24)

        # ---- left: where backups go
        left = _card()
        ll = QVBoxLayout(left)
        ll.setContentsMargins(24, 24, 24, 24)
        ll.setSpacing(12)
        ll.addWidget(_section_title("Where backups are saved"))
        hint = QLabel("Add at least one place that is NOT this computer's disk — a pendrive, "
                      "another drive, or a Google Drive / OneDrive folder (synced to the internet).")
        hint.setWordWrap(True)
        hint.setStyleSheet("font-size: 13px; color: #546E7A; background: transparent;")
        ll.addWidget(hint)

        self.dest_list = QListWidget()
        self.dest_list.setStyleSheet("""
            QListWidget { background-color: #F5F7FA; border: 1px solid #E0E6ED; border-radius: 10px;
                          padding: 6px; font-size: 13px; }
            QListWidget::item { padding: 10px; border-bottom: 1px solid #E0E6ED; }
            QListWidget::item:selected { background-color: #ECEFF1; color: #1A1A2E; }
        """)
        ll.addWidget(self.dest_list, stretch=1)

        row = QHBoxLayout()
        row.addWidget(_button("➕ Add Folder…", ACCENT, self.add_folder, outline=True))
        row.addWidget(_button("☁️ Find Google Drive / OneDrive", ACCENT, self.find_cloud, outline=True))
        row.addWidget(_button("Remove", "#C62828", self.remove_folder, outline=True))
        ll.addLayout(row)

        self.usb_check = QCheckBox("Also back up to any pendrive that is plugged in")
        self.usb_check.setChecked(bool(settings.get("backup_to_usb")))
        self.usb_check.setStyleSheet("font-size: 14px; background: transparent; padding: 6px 0;")
        self.usb_check.toggled.connect(lambda v: (settings.set("backup_to_usb", v), self.load_destinations()))
        ll.addWidget(self.usb_check)

        trow = QHBoxLayout()
        tl = QLabel("Daily backup time:")
        tl.setStyleSheet("font-size: 14px; background: transparent;")
        trow.addWidget(tl)
        self.time_edit = QTimeEdit()
        self.time_edit.setDisplayFormat("hh:mm AP")
        hh, mm = (settings.get("daily_backup_time") or "13:00").split(":")
        self.time_edit.setTime(QTime(int(hh), int(mm)))
        self.time_edit.timeChanged.connect(lambda t: settings.set("daily_backup_time", t.toString("HH:mm")))
        trow.addWidget(self.time_edit)
        trow.addStretch()
        ll.addLayout(trow)

        ll.addWidget(_button("💾 Back Up Now", "#2E7D32", self.backup_now))

        sep = QFrame()
        sep.setFixedHeight(1)
        sep.setStyleSheet("background-color: #E0E6ED;")
        ll.addWidget(sep)
        ll.addWidget(_section_title("Excel copies"))

        ll.addWidget(_button("📊 Export All Data to Excel…", "#1565C0", self.export_all, outline=True))
        mrow = QHBoxLayout()
        self.month_edit = QDateEdit()
        self.month_edit.setDisplayFormat("MMMM yyyy")
        self.month_edit.setDate(QDate.currentDate().addMonths(-1))
        self.month_edit.setCalendarPopup(True)
        mrow.addWidget(self.month_edit)
        mrow.addWidget(_button("🗓️ Monthly Stock Statement…", "#1565C0", self.export_month, outline=True))
        ll.addLayout(mrow)

        cols.addWidget(left, stretch=2)

        # ---- right: available backups
        right = _card()
        rl = QVBoxLayout(right)
        rl.setContentsMargins(24, 24, 24, 24)
        rl.setSpacing(12)
        rl.addWidget(_section_title("Available backups"))
        self.backup_list = BackupListWidget(self.service)
        rl.addWidget(self.backup_list, stretch=1)
        brow = QHBoxLayout()
        brow.addWidget(_button("♻️ Restore Selected", "#E65100", self.restore_selected))
        brow.addWidget(_button("📂 Restore From File…", "#E65100", self.restore_from_file, outline=True))
        brow.addStretch()
        brow.addWidget(_button("🔄 Refresh", ACCENT, self.backup_list.refresh, outline=True))
        rl.addLayout(brow)
        cols.addWidget(right, stretch=3)

        outer.addLayout(cols, stretch=1)
        main.addWidget(content, stretch=1)
        self.refresh_status()

    def create_header(self):
        header = QFrame()
        header.setFixedHeight(100)
        header.setStyleSheet("QFrame { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, "
                             "stop:0 #263238, stop:1 #455A64); }")
        hl = QHBoxLayout(header)
        hl.setContentsMargins(40, 0, 40, 0)
        icon = QLabel("🛡️")
        icon.setStyleSheet("font-size: 40px; background: transparent;")
        hl.addWidget(icon)
        tl = QVBoxLayout()
        t = QLabel("Backup & Restore")
        t.setStyleSheet("font-size: 28px; font-weight: bold; color: white; background: transparent;")
        s = QLabel("Keep copies of your data safe, and bring them back when needed")
        s.setStyleSheet("font-size: 14px; color: rgba(255,255,255,0.8); background: transparent;")
        tl.addWidget(t)
        tl.addWidget(s)
        hl.addLayout(tl)
        hl.addStretch()
        back = QPushButton("← Back")
        back.setCursor(Qt.CursorShape.PointingHandCursor)
        back.setStyleSheet("""
            QPushButton { background-color: rgba(255,255,255,0.2); color: white;
                          border: 2px solid rgba(255,255,255,0.5); border-radius: 8px;
                          padding: 10px 25px; font-size: 14px; font-weight: 600; }
            QPushButton:hover { background-color: rgba(255,255,255,0.3); }
        """)
        back.clicked.connect(self.close)
        hl.addWidget(back)
        return header

    # ---- destinations -------------------------------------------------------

    def refresh_status(self):
        style_banner(self.banner, self.service.status_summary())

    def load_destinations(self):
        self.dest_list.clear()
        status = settings.get("backup_status")
        for d in self.service.destinations():
            st = status.get(str(d.root), {})
            if st.get("ok"):
                line = f"✅  {d.label}\n      last backup {st['time'].replace('T', ' ')[:16]}"
            elif st.get("error"):
                line = f"❌  {d.label}\n      {st['error']}"
            else:
                line = f"⏳  {d.label}\n      no backup yet"
            if d.kind == "local":
                line += "   (same disk — not safe on its own)"
            item = QListWidgetItem(line)
            item.setData(Qt.ItemDataRole.UserRole, (d.kind, str(d.root)))
            self.dest_list.addItem(item)
        self.refresh_status()

    def _add_destination(self, path):
        dests = settings.get("backup_destinations")
        if path not in dests:
            dests.append(path)
            settings.set("backup_destinations", dests)

    def add_folder(self):
        path = QFileDialog.getExistingDirectory(self, "Choose a backup folder (pendrive, other drive, Google Drive…)")
        if not path:
            return
        from utils.db_path import get_app_data_dir
        if Path(path).resolve() == get_app_data_dir().resolve():
            QMessageBox.warning(self, "Choose Another Folder",
                                "That is the app's own data folder. Please pick a different location.")
            return
        self._add_destination(path)
        self.load_destinations()
        if QMessageBox.question(self, "Back Up Now?", f"Added:\n{path}\n\nMake a backup there now?") \
                == QMessageBox.StandardButton.Yes:
            self.backup_now()

    def find_cloud(self):
        found = detect_cloud_folders()
        if not found:
            QMessageBox.information(
                self, "Not Found",
                "Google Drive or OneDrive was not found on this computer.\n\n"
                "Install 'Google Drive for desktop' (free) and sign in, then try again — "
                "or use 'Add Folder…' to choose a folder yourself.")
            return
        names = "\n".join(f"•  {label}: {p}" for label, p in found)
        if QMessageBox.question(self, "Use These Folders?",
                                f"Found:\n{names}\n\nSave backups to these folders too?") \
                == QMessageBox.StandardButton.Yes:
            for _, p in found:
                self._add_destination(str(p))
            self.load_destinations()
            self.backup_now()

    def remove_folder(self):
        item = self.dest_list.currentItem()
        if not item:
            QMessageBox.information(self, "Remove", "Select a folder in the list first.")
            return
        kind, root = item.data(Qt.ItemDataRole.UserRole)
        if kind != "folder":
            QMessageBox.information(self, "Remove", "Only folders you added can be removed here.\n"
                                    "(Use the checkbox to turn pendrive backups off.)")
            return
        if QMessageBox.question(self, "Remove", f"Stop saving backups to:\n{root}\n\n"
                                "(Backups already saved there are NOT deleted.)") \
                == QMessageBox.StandardButton.Yes:
            settings.set("backup_destinations", [p for p in settings.get("backup_destinations") if p != root])
            self.load_destinations()

    # ---- actions ------------------------------------------------------------

    def backup_now(self):
        from services.backup_scheduler import get_scheduler
        from utils.db_path import get_log_dir
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            sched = get_scheduler()
            # The scheduler logs and returns None on failure
            result = sched.run_backup("manual", with_exports=True) if sched \
                else self.service.create_backup("manual")
        finally:
            QApplication.restoreOverrideCursor()
        self.load_destinations()
        self.backup_list.refresh()
        if not result:
            QMessageBox.critical(self, "Backup Failed",
                                 f"The backup could not be made.\n\nDetails are in:\n{get_log_dir() / 'app.log'}")
            return
        msg = "Saved to:\n" + "\n".join(f"  ✅ {s}" for s in result["succeeded"])
        if result["failed"]:
            msg += "\n\nFailed:\n" + "\n".join(f"  ❌ {l}: {e}" for l, e in result["failed"])
            QMessageBox.warning(self, "Backup Partly Done", msg)
        else:
            QMessageBox.information(self, "Backup Done", msg)

    def export_all(self):
        from services.export_service import export_full_data
        path, _ = QFileDialog.getSaveFileName(
            self, "Export All Data", f"Hospital_Stock_Full_Data_{date.today():%Y-%m-%d}.xlsx",
            "Excel Files (*.xlsx)")
        if path:
            if not path.lower().endswith(".xlsx"):
                path += ".xlsx"
            export_full_data(path)
            QMessageBox.information(self, "Exported", f"All data exported to:\n{path}")

    def export_month(self):
        from services.export_service import export_monthly_snapshot
        d = self.month_edit.date()
        path, _ = QFileDialog.getSaveFileName(
            self, "Monthly Stock Statement", f"Stock_Statement_{d.year()}-{d.month():02d}.xlsx",
            "Excel Files (*.xlsx)")
        if path:
            if not path.lower().endswith(".xlsx"):
                path += ".xlsx"
            export_monthly_snapshot(d.year(), d.month(), path)
            QMessageBox.information(self, "Exported", f"Stock statement saved to:\n{path}")

    def restore_selected(self):
        b = self.backup_list.selected()
        if not b:
            QMessageBox.information(self, "Restore", "Select a backup in the list first.")
            return
        if confirm_and_restore(self, self.service, b.path):
            restart_app()

    def restore_from_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Choose a backup or recovered database file", "",
            "Database files (*.db *.sqlite *.sqlite3);;All files (*)")
        if path and confirm_and_restore(self, self.service, Path(path)):
            restart_app()


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
        self.resize(900, 600)
        self.setStyleSheet("background-color: white;")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(14)

        heading = QLabel(title)
        heading.setStyleSheet("font-size: 22px; font-weight: bold; color: #1A1A2E;")
        layout.addWidget(heading)
        msg = QLabel(message)
        msg.setWordWrap(True)
        msg.setStyleSheet("font-size: 14px; color: #37474F;")
        layout.addWidget(msg)

        self.backup_list = BackupListWidget(service)
        layout.addWidget(self.backup_list, stretch=1)

        row = QHBoxLayout()
        row.addWidget(_button("♻️ Restore Selected", "#E65100", self.restore_selected))
        row.addWidget(_button("📂 Restore From File…", "#E65100", self.restore_from_file, outline=True))
        row.addStretch()
        row.addWidget(_button("Continue Without Restoring", "#546E7A", self.reject, outline=True))
        layout.addLayout(row)

        self.backup_list.refresh()

    def _do_restore(self, path):
        if confirm_and_restore(self, self.service, path):
            self.restored = True
            self.accept()

    def restore_selected(self):
        b = self.backup_list.selected()
        if b:
            self._do_restore(b.path)

    def restore_from_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Choose a backup or recovered database file", "",
            "Database files (*.db *.sqlite *.sqlite3);;All files (*)")
        if path:
            self._do_restore(Path(path))
