"""
Backup and restore.

WHY THIS EXISTS: the old version kept its only backups in a folder next to the
database, on the same hard disk, and only the last 10. When that disk failed,
the data and every backup went with it.

Now each backup is:
  * a consistent snapshot made with SQLite's backup API (safe while the app is open)
  * verified with an integrity check before it is kept
  * copied to EVERY destination:
        - the local backups folder (fast restores, but same disk)
        - each folder the user adds (second drive, Google Drive / OneDrive folder ...)
        - any USB pendrive that is plugged in (if enabled)
  * pruned with a tiered retention so you can go back days, weeks and months:
        last 20 backups + 1 per day for 60 days + 1 per week for 26 weeks
        + 1 per month forever

Each destination gets a "HospitalStockBackups" folder. Backup file names look
like  hospital_20261119_181502_daily.db  (date, time, reason).
"""
import logging
import os
import re
import shutil
import sqlite3
import sys
import tempfile
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

from utils import settings
from utils.db_path import get_local_backup_dir

log = logging.getLogger(__name__)

BACKUP_FOLDER_NAME = "HospitalStockBackups"
_NAME_RE = re.compile(r"^hospital_(\d{8})_(\d{6})_([a-z]+)\.db$")
_LEGACY_RE = re.compile(r"^hospital_backup_(\d{8})_(\d{6})\.db$")  # old version's files

KEEP_LAST = 20
KEEP_DAILY_DAYS = 60
KEEP_WEEKLY_WEEKS = 26
KEEP_PROTECTED_DAYS = 90
PROTECTED_REASONS = {"manual", "prerestore", "premigrate"}

REASON_LABELS = {
    "auto": "Auto (after changes)",
    "daily": "Daily",
    "startup": "App start",
    "exit": "App close",
    "manual": "Manual",
    "usb": "Pendrive inserted",
    "prerestore": "Before restore",
    "premigrate": "Before upgrade",
    "legacy": "Old version",
}


@dataclass
class Destination:
    label: str        # shown to the user
    root: Path        # the drive/folder the user picked
    kind: str         # "local", "folder" or "usb"

    @property
    def folder(self) -> Path:
        if self.kind == "local":
            return self.root
        return self.root / BACKUP_FOLDER_NAME

    @property
    def offsite(self) -> bool:
        return self.kind != "local"


@dataclass
class BackupInfo:
    path: Path
    time: datetime
    reason: str
    size: int
    location: str

    @property
    def reason_label(self):
        return REASON_LABELS.get(self.reason, self.reason)


# ---------------------------------------------------------------------------
# Drive / cloud-folder detection
# ---------------------------------------------------------------------------

def detect_removable_drives():
    """Root paths of plugged-in USB pendrives / removable disks."""
    drives = []
    try:
        if sys.platform == "win32":
            import ctypes
            import string
            bitmask = ctypes.windll.kernel32.GetLogicalDrives()
            for i, letter in enumerate(string.ascii_uppercase):
                if bitmask & (1 << i):
                    root = f"{letter}:\\"
                    if ctypes.windll.kernel32.GetDriveTypeW(root) == 2:  # DRIVE_REMOVABLE
                        if os.path.exists(root):  # skip empty card readers
                            drives.append(Path(root))
        elif sys.platform == "darwin":
            volumes = Path("/Volumes")
            if volumes.exists():
                for v in volumes.iterdir():
                    # The startup disk appears as a symlink to "/"
                    if v.is_dir() and not v.is_symlink() and os.access(v, os.W_OK):
                        drives.append(v)
        else:
            user = os.environ.get("USER", "")
            for base in (Path("/media") / user, Path("/run/media") / user):
                if base.exists():
                    drives.extend(p for p in base.iterdir() if p.is_dir())
    except Exception:
        log.exception("Could not list removable drives")
    return drives


def detect_cloud_folders():
    """
    Folders synced by Google Drive for Desktop or OneDrive, if installed.
    Backups saved there are uploaded automatically = an off-site copy.
    Returns a list of (label, Path).
    """
    found = []
    home = Path.home()

    def add(label, path):
        try:
            if path.exists() and path.is_dir() and all(p != path for _, p in found):
                found.append((label, path))
        except OSError:
            pass

    if sys.platform == "win32":
        import string
        for env in ("OneDrive", "OneDriveConsumer", "OneDriveCommercial"):
            if os.environ.get(env):
                add("OneDrive", Path(os.environ[env]))
        for letter in string.ascii_uppercase[3:]:  # D: .. Z:
            add("Google Drive", Path(f"{letter}:\\My Drive"))
        add("Google Drive", home / "Google Drive" / "My Drive")
        add("Google Drive", home / "Google Drive")
    elif sys.platform == "darwin":
        cloud = home / "Library" / "CloudStorage"
        if cloud.exists():
            for p in cloud.iterdir():
                if p.name.startswith("GoogleDrive"):
                    add("Google Drive", p / "My Drive")
                elif p.name.startswith("OneDrive"):
                    add("OneDrive", p)
        add("Google Drive", home / "Google Drive" / "My Drive")
        add("OneDrive", home / "OneDrive")
    else:
        add("Google Drive", home / "GoogleDrive")
        add("OneDrive", home / "OneDrive")
    return found


# ---------------------------------------------------------------------------
# Database file checks
# ---------------------------------------------------------------------------

def inspect_database(path):
    """
    Open a database file read-only and summarise it, so the user can see what a
    backup contains before restoring it. Never modifies the file.
    """
    path = Path(path)
    info = {"ok": False, "error": None, "path": str(path)}
    try:
        uri = path.resolve().as_uri() + "?mode=ro"
        conn = sqlite3.connect(uri, uri=True)
        try:
            result = conn.execute("PRAGMA quick_check").fetchone()[0]
            if result != "ok":
                info["error"] = f"File is damaged ({result})"
                return info
            tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            if not {"items", "vendors", "bills", "stock_register"} <= tables:
                info["error"] = "This is not a Hospital Stock database"
                return info

            def one(q):
                return conn.execute(q).fetchone()[0]

            info.update(
                ok=True,
                schema_version=one("PRAGMA user_version"),
                items=one("SELECT COUNT(*) FROM items"),
                vendors=one("SELECT COUNT(*) FROM vendors"),
                bills=one("SELECT COUNT(*) FROM bills"),
                issues=one("SELECT COUNT(*) FROM stock_register WHERE issued_qty > 0"),
                last_invoice=one("SELECT MAX(COALESCE(invoice_date, entry_date)) FROM bills"),
                last_issue=one("SELECT MAX(date) FROM stock_register WHERE issued_qty > 0"),
            )
        finally:
            conn.close()
    except sqlite3.DatabaseError as e:
        info["error"] = f"Not a readable database ({e})"
    except Exception as e:
        info["error"] = str(e)
    return info


def check_integrity(db_path):
    """Full integrity check of a database file. Returns (ok, message)."""
    try:
        conn = sqlite3.connect(str(db_path))
        try:
            rows = conn.execute("PRAGMA integrity_check").fetchall()
        finally:
            conn.close()
        msg = "; ".join(r[0] for r in rows[:5])
        return msg == "ok", msg
    except sqlite3.DatabaseError as e:
        return False, str(e)


# ---------------------------------------------------------------------------
# Retention
# ---------------------------------------------------------------------------

def select_backups_to_keep(backups, now=None):
    """
    Given BackupInfo objects from ONE folder, return the set of paths to keep:
    last 20, newest per day (60 days), per week (26 weeks), per month (forever),
    plus manual / pre-restore / pre-upgrade backups for 90 days.
    """
    now = now or datetime.now()
    ordered = sorted(backups, key=lambda b: b.time, reverse=True)
    keep = {b.path for b in ordered[:KEEP_LAST]}

    seen_day, seen_week, seen_month = set(), set(), set()
    for b in ordered:  # newest first, so the first seen in each bucket is the newest
        age = now - b.time
        day = b.time.date()
        week = b.time.isocalendar()[:2]
        month = (b.time.year, b.time.month)
        if age <= timedelta(days=KEEP_DAILY_DAYS) and day not in seen_day:
            keep.add(b.path)
        if age <= timedelta(weeks=KEEP_WEEKLY_WEEKS) and week not in seen_week:
            keep.add(b.path)
        if month not in seen_month:
            keep.add(b.path)
        if b.reason in PROTECTED_REASONS and age <= timedelta(days=KEEP_PROTECTED_DAYS):
            keep.add(b.path)
        seen_day.add(day)
        seen_week.add(week)
        seen_month.add(month)
    return keep


# ---------------------------------------------------------------------------
# The service
# ---------------------------------------------------------------------------

def _parse_backup(path, location):
    m = _NAME_RE.match(path.name)
    legacy = _LEGACY_RE.match(path.name) if not m else None
    if not (m or legacy):
        return None
    g = m or legacy
    try:
        when = datetime.strptime(g.group(1) + g.group(2), "%Y%m%d%H%M%S")
        size = path.stat().st_size
    except (ValueError, OSError):
        return None
    reason = m.group(3) if m else "legacy"
    return BackupInfo(path=path, time=when, reason=reason, size=size, location=location)


def _list_folder(folder, location):
    out = []
    try:
        if folder.exists():
            for p in folder.iterdir():
                info = _parse_backup(p, location)
                if info:
                    out.append(info)
    except OSError:
        log.warning("Could not read backup folder %s", folder)
    return out


class BackupService:
    def __init__(self, db):
        self.db = db  # DatabaseService

    # ---- destinations --------------------------------------------------------

    def destinations(self, include_usb=None):
        dests = [Destination("This computer (same disk)", get_local_backup_dir(), "local")]
        for p in settings.get("backup_destinations"):
            dests.append(Destination(p, Path(p), "folder"))
        if include_usb is None:
            include_usb = settings.get("backup_to_usb")
        if include_usb:
            configured = {str(d.root) for d in dests}
            for drive in detect_removable_drives():
                if str(drive) not in configured:
                    dests.append(Destination(f"Pendrive {drive}", drive, "usb"))
        return dests

    # ---- creating backups ----------------------------------------------------

    def create_backup(self, reason="manual", destinations=None):
        """
        Make one verified snapshot and copy it to every destination.
        Returns {"file": name, "succeeded": [labels], "failed": [(label, error)]}.
        Raises RuntimeError if the snapshot itself could not be made.
        """
        dests = destinations if destinations is not None else self.destinations()
        name = f"hospital_{datetime.now():%Y%m%d_%H%M%S}_{reason}.db"
        local_dir = get_local_backup_dir()
        fd, tmp = tempfile.mkstemp(dir=str(local_dir), prefix=".snapshot_", suffix=".db")
        os.close(fd)
        tmp = Path(tmp)
        result = {"file": name, "succeeded": [], "failed": []}
        try:
            # 1. Consistent snapshot via SQLite's online backup API
            target = sqlite3.connect(str(tmp))
            try:
                self.db.conn.backup(target)
            finally:
                target.close()

            # 2. Verify before trusting it
            ok, msg = check_integrity(tmp)
            if not ok:
                raise RuntimeError(f"Backup snapshot failed its integrity check: {msg}")

            # 3. Copy to every destination
            status = settings.get("backup_status")
            now_iso = datetime.now().isoformat(timespec="seconds")
            for d in dests:
                try:
                    if d.kind != "local" and not d.root.exists():
                        raise FileNotFoundError(f"{d.root} is not available (drive unplugged?)")
                    d.folder.mkdir(parents=True, exist_ok=True)
                    final = d.folder / name
                    part = d.folder / (name + ".part")
                    shutil.copyfile(tmp, part)
                    os.replace(part, final)  # only complete files ever get the real name
                    self.prune(d.folder, d.label)
                    result["succeeded"].append(d.label)
                    status[str(d.root)] = {"time": now_iso, "ok": True, "error": "",
                                           "kind": d.kind, "label": d.label}
                except Exception as e:
                    log.warning("Backup to %s failed: %s", d.label, e)
                    result["failed"].append((d.label, str(e)))
                    prev = status.get(str(d.root), {})
                    status[str(d.root)] = {**prev, "ok": False, "error": str(e),
                                           "failed_time": now_iso, "kind": d.kind, "label": d.label}
            settings.set("backup_status", status)
            if result["succeeded"]:
                settings.set("last_backup_time", now_iso)
            log.info("Backup %s: ok=%s failed=%s", name, result["succeeded"], result["failed"])
            return result
        finally:
            try:
                tmp.unlink()
            except OSError:
                pass

    def prune(self, folder, location=""):
        """Delete old backups in one folder according to the retention rules."""
        backups = [b for b in _list_folder(folder, location) if b.reason != "legacy"]
        keep = select_backups_to_keep(backups)
        for b in backups:
            if b.path not in keep:
                try:
                    b.path.unlink()
                except OSError:
                    log.warning("Could not delete old backup %s", b.path)

    # ---- listing -------------------------------------------------------------

    def candidate_folders(self):
        """Every place backups might be: destinations plus any detected drive or cloud folder."""
        folders = [(d.label, d.folder) for d in self.destinations(include_usb=True)]
        for drive in detect_removable_drives():
            folders.append((f"Pendrive {drive}", drive / BACKUP_FOLDER_NAME))
        for label, path in detect_cloud_folders():
            folders.append((label, path / BACKUP_FOLDER_NAME))
        unique, seen = [], set()
        for label, folder in folders:
            key = os.path.normcase(str(folder))
            if key not in seen:
                seen.add(key)
                unique.append((label, folder))
        return unique

    def list_backups(self):
        """All backups found in every known location, newest first."""
        found = []
        for label, folder in self.candidate_folders():
            found.extend(_list_folder(folder, label))
        found.sort(key=lambda b: b.time, reverse=True)
        return found

    # ---- restore -------------------------------------------------------------

    def restore(self, backup_path):
        """
        Replace the live database with a backup file. A safety backup of the
        current data is made first, so a restore can itself be undone.
        After this returns the app should be restarted.
        """
        from models.migrations import migrate

        backup_path = Path(backup_path)
        info = inspect_database(backup_path)
        if not info["ok"]:
            raise RuntimeError(f"Cannot restore this file: {info['error']}")

        db_path = Path(self.db.db_path)

        # Safety copy of what we have now (may fail if the current DB is damaged)
        safety_ok = False
        if self.db.conn is not None:
            try:
                safety_ok = bool(self.create_backup("prerestore")["succeeded"])
            except Exception:
                log.exception("Pre-restore safety backup failed")
        if not safety_ok and db_path.exists():
            # Keep the raw file untouched so nothing is ever thrown away
            raw = get_local_backup_dir() / f"replaced_{datetime.now():%Y%m%d_%H%M%S}.db"
            try:
                shutil.copyfile(db_path, raw)
                log.info("Kept a raw copy of the replaced database at %s", raw)
            except OSError:
                log.exception("Could not keep a raw copy of the replaced database")

        staged = db_path.with_name(db_path.name + ".restoring")
        shutil.copyfile(backup_path, staged)

        self.db.close()
        for suffix in ("-wal", "-shm"):
            try:
                Path(str(db_path) + suffix).unlink()
            except FileNotFoundError:
                pass
        os.replace(staged, db_path)
        self.db.connect()
        migrate(self.db.conn)  # an older backup is upgraded to the current schema
        log.info("Restored database from %s", backup_path)

    # ---- status for the dashboard -------------------------------------------

    def status_summary(self):
        """
        Returns dict(level, text) where level is "ok", "warn" or "danger".
        """
        status = settings.get("backup_status")
        warn_days = settings.get("offsite_warning_days") or 3
        configured = settings.get("backup_destinations")

        offsite_times = []
        for entry in status.values():
            if entry.get("kind") in ("folder", "usb") and entry.get("time"):
                try:
                    offsite_times.append(datetime.fromisoformat(entry["time"]))
                except ValueError:
                    pass
        last_any = settings.get("last_backup_time")
        last_offsite = max(offsite_times) if offsite_times else None

        def ago(t):
            delta = datetime.now() - t
            if delta < timedelta(minutes=2):
                return "just now"
            if delta < timedelta(hours=1):
                return f"{int(delta.total_seconds() // 60)} min ago"
            if delta < timedelta(days=1):
                return f"{int(delta.total_seconds() // 3600)} hours ago"
            return f"{delta.days} days ago ({t:%d %b %Y})"

        # Only folders still configured count (a removed folder's old failure is ignored)
        failing = [status[p].get("label", p) for p in configured
                   if p in status and not status[p].get("ok")]

        if not configured and not last_offsite:
            return {"level": "danger",
                    "text": "No off-site backup is set up. If this computer's disk fails, all data "
                            "will be lost. Open Backup & Restore to add a pendrive or Google Drive folder."}
        if not last_offsite or datetime.now() - last_offsite > timedelta(days=warn_days):
            when = ago(last_offsite) if last_offsite else "never"
            return {"level": "danger",
                    "text": f"Last off-site backup: {when}. Plug in the backup pendrive or check "
                            f"the backup folder in Backup & Restore."}
        if failing:
            return {"level": "warn",
                    "text": f"Backup folder not reachable: {', '.join(failing)}. "
                            f"Last off-site backup {ago(last_offsite)}."}
        text = f"Last off-site backup {ago(last_offsite)}"
        if last_any:
            try:
                text += f" · last backup {ago(datetime.fromisoformat(last_any))}"
            except ValueError:
                pass
        return {"level": "ok", "text": text}
