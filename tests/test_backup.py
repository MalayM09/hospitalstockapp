"""Backups, retention, restore, exports."""
import os
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from services.backup_service import (
    BACKUP_FOLDER_NAME, BackupInfo, BackupService, check_integrity, inspect_database, select_backups_to_keep,
)
from services.bill_service import BillService
from utils import settings


def test_backup_to_all_destinations_and_status(db, ids, tmp_path):
    off = tmp_path / "gdrive"
    off.mkdir()
    settings.set("backup_destinations", [str(off), str(tmp_path / "unplugged")])
    svc = BackupService(db)
    r = svc.create_backup("manual")
    assert len(r["succeeded"]) == 2 and len(r["failed"]) == 1
    f = list((off / BACKUP_FOLDER_NAME).glob("hospital_*.db"))
    assert len(f) == 1 and inspect_database(f[0])["ok"]
    assert not list((off / BACKUP_FOLDER_NAME).glob("*.part"))
    assert svc.status_summary()["level"] == "warn"  # one folder unreachable
    settings.set("backup_destinations", [str(off)])
    svc.create_backup("auto")
    assert svc.status_summary()["level"] == "ok"


def test_no_offsite_backup_is_flagged(db):
    assert BackupService(db).status_summary()["level"] == "danger"


def test_retention_policy():
    now = datetime(2026, 11, 19, 12)
    fake = [BackupInfo(Path(f"f{i}"), now - timedelta(hours=4 * i), "auto", 1, "x") for i in range(2000)]
    keep = select_backups_to_keep(fake, now=now)
    kept = [b for b in fake if b.path in keep]
    months = {(b.time.year, b.time.month) for b in fake}
    assert months == {(b.time.year, b.time.month) for b in kept}
    assert len(keep) < 150
    assert sum(1 for b in kept if now - b.time <= timedelta(days=60)) >= 60


def test_prune_only_touches_backup_files(db, tmp_path):
    now = datetime.now()
    for i in range(40):
        t = now - timedelta(minutes=10 * i)
        (tmp_path / f"hospital_{t:%Y%m%d_%H%M%S}_auto.db").write_bytes(b"x")
    (tmp_path / "notes.txt").write_text("keep")
    BackupService(db).prune(tmp_path)
    assert len(list(tmp_path.glob("hospital_*.db"))) == 20
    assert (tmp_path / "notes.txt").exists()


def test_restore_round_trip_and_bad_files(db, ids, data_dir, tmp_path):
    svc = BackupService(db)
    bs = BillService()
    bs.add_bill(ids["crp"], ids["vendor"], "BEFORE", "2026-05-10", "", None, 1, 1, 0)
    snap = Path(data_dir / "backups") / svc.create_backup("manual")["file"]
    bs.add_bill(ids["crp"], ids["vendor"], "AFTER", "2026-05-11", "", None, 1, 1, 0)
    svc.restore(snap)
    assert db.scalar("SELECT COUNT(*) FROM bills") == 1
    assert any("prerestore" in f.name for f in (data_dir / "backups").iterdir())

    bad = tmp_path / "bad.db"
    bad.write_bytes(b"SQLite format 3\x00" + os.urandom(4000))
    assert not inspect_database(bad)["ok"]
    other = tmp_path / "other.db"
    c = sqlite3.connect(other)
    c.execute("CREATE TABLE x (a)")
    c.close()
    assert inspect_database(other)["error"] == "This is not a Hospital Stock database"
    with pytest.raises(RuntimeError):
        svc.restore(bad)
    assert check_integrity(data_dir / "hospital.db")[0]


def test_excel_exports(db, ids, tmp_path):
    from openpyxl import load_workbook
    from services.export_service import export_full_data, export_monthly_snapshot, export_report
    from services.report_service import ReportService
    BillService().add_bill(ids["crp"], ids["vendor"], "X", "2026-05-10", "", None, 25, 10, 0)
    wb = load_workbook(export_full_data(tmp_path / "full.xlsx"))
    assert wb.sheetnames == ["Stock Summary", "Purchases", "Issues", "All Stock Movements", "Items", "Vendors"]
    ws = load_workbook(export_monthly_snapshot(2026, 5, tmp_path / "may.xlsx"))["Stock Statement"]
    rows = {r[0]: r[1:] for r in ws.iter_rows(min_row=4, values_only=True)}
    assert rows["CRP"] == (0, 25, 0, 25)
    rep = ReportService().purchases_by_period("2026-05-01", "2026-05-31", "month")
    ws = load_workbook(export_report(rep, tmp_path / "r.xlsx")).active
    values = [r for r in ws.iter_rows(min_row=4, values_only=True)]
    assert values[0][0] == "May 2026" and values[0][5] == 250 and values[-1][0] == "Total"
