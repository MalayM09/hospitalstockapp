"""
Small JSON settings store.

Settings live in a JSON file next to the database rather than inside it, so
that backup configuration survives even if the database itself is damaged.
"""
import json
import logging
import os
import tempfile
import threading

from utils.db_path import get_settings_path

log = logging.getLogger(__name__)

DEFAULTS = {
    # Extra backup folders (second drive, Google Drive / OneDrive folder, ...)
    "backup_destinations": [],
    # Also back up to any USB pendrive that is plugged in
    "backup_to_usb": True,
    # Daily backup time (24h "HH:MM") - runs if the app is open at/after this time
    "daily_backup_time": "13:00",
    # Warn if no backup has reached an off-site destination for this many days
    "offsite_warning_days": 3,
    # Per-destination status: {path: {"time": iso, "ok": bool, "error": str}}
    "backup_status": {},
    # ISO timestamp of the last successful backup to any destination
    "last_backup_time": None,
    # Date ("YYYY-MM-DD") of the last successful daily backup
    "last_daily_backup_date": None,
}

_lock = threading.Lock()


def _load():
    path = get_settings_path()
    if not path.exists():
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        log.exception("settings.json is unreadable - using defaults")
        return {}


def get(key):
    with _lock:
        data = _load()
    if key in data:
        return data[key]
    default = DEFAULTS.get(key)
    # Return copies of mutable defaults so callers can't modify DEFAULTS
    if isinstance(default, (list, dict)):
        return type(default)(default)
    return default


def set(key, value):
    with _lock:
        data = _load()
        data[key] = value
        path = get_settings_path()
        # Write atomically: temp file + rename, so a crash can't leave half a file
        fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=".settings_", suffix=".json")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            os.replace(tmp, path)
        except Exception:
            try:
                os.unlink(tmp)
            except OSError:
                pass
            raise
