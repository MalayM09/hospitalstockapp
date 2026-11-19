import logging
from datetime import date
from pathlib import Path

from PyQt6.QtCore import QDate, QSize, Qt, QTime
from PyQt6.QtWidgets import (
    QApplication, QCheckBox, QDateEdit, QFileDialog, QHBoxLayout, QLabel, QListWidget, QListWidgetItem,
    QTimeEdit,
)

from services.backup_service import BackupService, detect_cloud_folders
from services.db_service import get_db
from ui.backup_ui import BackupList, confirm_and_restore, restart_app
from ui.pages.base import Page
from ui.theme import COLORS, icon
from ui.widgets import Card, alert, button, confirm, divider, label, toast, uniform_height
from utils import settings
from utils.db_path import get_app_data_dir, get_log_dir

log = logging.getLogger(__name__)


class BackupPage(Page):
    nav_key = "backup"
    title = "Backup & Restore"
    subtitle = "Keep copies of your data in more than one place"

    def __init__(self, main):
        super().__init__(main)
        self.service = BackupService(get_db())
        self.header.add_action(button("Back up now", "primary", "cloud-arrow-up", "Make a backup everywhere now",
                                      self.backup_now))

        self.banner = QLabel()
        self.banner.setWordWrap(True)
        self.root.addWidget(self.banner)

        body = QHBoxLayout()
        body.setSpacing(16)

        left = Card(margins=(20, 18, 20, 18), spacing=10)
        left.setFixedWidth(430)
        left.add(label("Where backups are saved", "cardTitle"))
        left.add(label("Add at least one place that is NOT this computer's disk — a pendrive, another drive, "
                       "or a Google Drive / OneDrive folder.", "caption", wrap=True))
        self.dest_list = QListWidget()
        self.dest_list.setIconSize(QSize(18, 18))
        left.add(self.dest_list, 1)
        row = QHBoxLayout()
        row.addWidget(button("Add folder…", None, "folder-plus", callback=self.add_folder))
        row.addWidget(button("Find Google Drive", None, "cloud", "Find Google Drive / OneDrive folders",
                             self.find_cloud))
        row.addWidget(button("Remove", "danger", None, callback=self.remove_folder))
        left.add(row)
        self.usb = QCheckBox("Also back up to any pendrive that is plugged in")
        self.usb.setChecked(bool(settings.get("backup_to_usb")))
        self.usb.toggled.connect(lambda v: (settings.set("backup_to_usb", v), self.load_destinations()))
        left.add(self.usb)
        trow = QHBoxLayout()
        trow.addWidget(label("Daily backup at"))
        self.time = uniform_height(QTimeEdit())
        self.time.setDisplayFormat("hh:mm AP")
        hh, mm = (settings.get("daily_backup_time") or "13:00").split(":")
        self.time.setTime(QTime(int(hh), int(mm)))
        self.time.timeChanged.connect(lambda t: settings.set("daily_backup_time", t.toString("HH:mm")))
        trow.addWidget(self.time)
        trow.addStretch()
        left.add(trow)
        left.add(divider())
        left.add(label("Excel copies", "cardTitle"))
        left.add(button("Export all data to Excel…", None, "file-arrow-down", callback=self.export_all))
        mrow = QHBoxLayout()
        self.month = uniform_height(QDateEdit(QDate.currentDate().addMonths(-1)))
        self.month.setDisplayFormat("MMMM yyyy")
        self.month.setCalendarPopup(True)
        mrow.addWidget(self.month, 1)
        mrow.addWidget(button("Monthly statement…", None, "calendar-blank", callback=self.export_month))
        left.add(mrow)
        body.addWidget(left)

        right = Card(margins=(18, 16, 18, 16), spacing=10)
        right.add(label("Available backups", "cardTitle"))
        self.list = BackupList(self.service)
        right.add(self.list, 1)
        brow = QHBoxLayout()
        brow.addWidget(button("Restore selected", None, "arrow-counter-clockwise", callback=self.restore_selected))
        brow.addWidget(button("Restore from file…", None, "folder-open", callback=self.restore_from_file))
        brow.addStretch()
        brow.addWidget(button("Refresh", "ghost", "arrows-clockwise", "Look for backups again", self.list.refresh))
        right.add(brow)
        body.addWidget(right, 1)
        self.root.addLayout(body, 1)
        self._listed = False

    # ---- status ------------------------------------------------------------------

    def refresh(self):
        s = self.service.status_summary()
        fg, bg, ic = {"ok": (COLORS["success"], COLORS["success_soft"], "check-circle"),
                      "warn": (COLORS["warning"], COLORS["warning_soft"], "warning-circle"),
                      "danger": (COLORS["danger"], COLORS["danger_soft"], "warning-circle")}[s["level"]]
        self.banner.setText(s["text"])
        self.banner.setStyleSheet(f"background:{bg}; color:{fg}; border-radius:8px; padding:11px 14px;"
                                  f"font-weight:600;")
        self.load_destinations()
        if not self._listed:  # scanning drives can be slow; do it once, then on demand
            self.list.refresh()
            self._listed = True

    def load_destinations(self):
        self.dest_list.clear()
        status = settings.get("backup_status")
        for d in self.service.destinations():
            st = status.get(str(d.root), {})
            if st.get("ok"):
                ic, color, sub = "check-circle", COLORS["success"], f"Last backup {st['time'].replace('T', ' ')[:16]}"
            elif st.get("error"):
                ic, color, sub = "x-circle", COLORS["danger"], st["error"]
            else:
                ic, color, sub = "clock", COLORS["faint"], "No backup yet"
            if d.kind == "local":
                sub += "  ·  same disk, not safe on its own"
            it = QListWidgetItem(icon(ic, color), f"{d.label}\n{sub}")
            it.setData(Qt.ItemDataRole.UserRole, (d.kind, str(d.root)))
            it.setToolTip(str(d.folder))
            self.dest_list.addItem(it)

    # ---- destinations ------------------------------------------------------------

    def _add_destination(self, path):
        dests = settings.get("backup_destinations")
        if path not in dests:
            dests.append(path)
            settings.set("backup_destinations", dests)

    def add_folder(self):
        path = QFileDialog.getExistingDirectory(self, "Choose a backup folder (pendrive, other drive, Google Drive…)")
        if not path:
            return
        if Path(path).resolve() == get_app_data_dir().resolve():
            alert(self, "Choose another folder", "That is the app's own data folder. Pick a different place.")
            return
        self._add_destination(path)
        self.load_destinations()
        if confirm(self, "Back up now?", f"Added:\n{path}\n\nMake a backup there now?", ok_text="Back up now",
                   danger=False):
            self.backup_now()

    def find_cloud(self):
        found = detect_cloud_folders()
        if not found:
            alert(self, "Not found", "Google Drive or OneDrive was not found on this computer.\n\n"
                  "Install 'Google Drive for desktop' (free) and sign in, then try again — or use "
                  "'Add folder…' to choose a folder yourself.", "info")
            return
        names = "\n".join(f"• {lbl}: {p}" for lbl, p in found)
        if confirm(self, "Use these folders?", f"Found:\n{names}\n\nSave backups there too?",
                   ok_text="Use them", danger=False):
            for _, p in found:
                self._add_destination(str(p))
            self.load_destinations()
            self.backup_now()

    def remove_folder(self):
        it = self.dest_list.currentItem()
        if not it:
            toast(self, "Select a folder in the list first", "info")
            return
        kind, root = it.data(Qt.ItemDataRole.UserRole)
        if kind != "folder":
            alert(self, "Can't remove", "Only folders you added can be removed. Use the checkbox to turn "
                  "pendrive backups off.", "info")
            return
        if confirm(self, "Stop backing up here?", f"{root}\n\nBackups already saved there are kept.",
                   ok_text="Remove", danger=True):
            settings.set("backup_destinations", [p for p in settings.get("backup_destinations") if p != root])
            self.load_destinations()

    # ---- actions -----------------------------------------------------------------

    def backup_now(self):
        from services.backup_scheduler import get_scheduler
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            sched = get_scheduler()
            result = sched.run_backup("manual", with_exports=True) if sched else self.service.create_backup("manual")
        finally:
            QApplication.restoreOverrideCursor()
        self.refresh()
        self.list.refresh()
        if not result:
            alert(self, "Backup failed", f"The backup could not be made.\n\nDetails: {get_log_dir() / 'app.log'}",
                  "error")
        elif result["failed"]:
            alert(self, "Backup partly done",
                  "Saved to:\n" + "\n".join(f"  ✓ {s}" for s in result["succeeded"]) +
                  "\n\nFailed:\n" + "\n".join(f"  ✗ {l}: {e}" for l, e in result["failed"]))
        else:
            toast(self, f"Backed up to {len(result['succeeded'])} location{'s' if len(result['succeeded']) != 1 else ''}")

    def export_all(self):
        from services.export_service import export_full_data
        path, _ = QFileDialog.getSaveFileName(self, "Export all data",
                                              f"Lab_Stock_Full_Data_{date.today():%Y-%m-%d}.xlsx",
                                              "Excel files (*.xlsx)")
        if path:
            if not path.lower().endswith(".xlsx"):
                path += ".xlsx"
            export_full_data(path)
            toast(self, "All data exported")

    def export_month(self):
        from services.export_service import export_monthly_snapshot
        d = self.month.date()
        path, _ = QFileDialog.getSaveFileName(self, "Monthly stock statement",
                                              f"Stock_Statement_{d.year()}-{d.month():02d}.xlsx",
                                              "Excel files (*.xlsx)")
        if path:
            if not path.lower().endswith(".xlsx"):
                path += ".xlsx"
            export_monthly_snapshot(d.year(), d.month(), path)
            toast(self, "Monthly statement saved")

    def restore_selected(self):
        b = self.list.selected()
        if not b:
            toast(self, "Select a backup first", "info")
            return
        if confirm_and_restore(self, self.service, b.path):
            alert(self, "Restored", "Backup restored. The app will now restart.", "info")
            restart_app()

    def restore_from_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "Choose a backup or recovered database file", "",
                                              "Database files (*.db *.sqlite *.sqlite3);;All files (*)")
        if path and confirm_and_restore(self, self.service, Path(path)):
            alert(self, "Restored", "Backup restored. The app will now restart.", "info")
            restart_app()
