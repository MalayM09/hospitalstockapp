"""Business logic: stock, bills, GST, masters, users, reports, migrations."""
import sqlite3

import pytest

from services.bill_service import BillService
from services.gst import compute_totals, invoice_totals
from services.master_service import MasterError
from services.stock_service import StockError, StockService


def line(item_id, qty, rate, gst=18, batch="", expiry=None):
    return {"item_id": item_id, "quantity": qty, "rate": rate, "gst_rate": gst,
            "batch_number": batch, "expiry_date": expiry}


# ---------------------------------------------------------------- GST

def test_gst_single_line():
    t = compute_totals(10, 100, 18)
    assert (t["amount"], t["cgst"], t["sgst"], t["igst"], t["net_amount"]) == (1000, 90, 90, 0, 1180)
    t = compute_totals(3, 33.33, 5, interstate=True)
    assert t["igst"] == 5.0 and t["net_amount"] == 105 and abs(t["round_off"] - 0.01) < 1e-9


def test_invoice_rounds_once_not_per_line():
    # Two lines of 0.40 each: per-line rounding would give 0 + 0; correct total is 0.80 -> 1
    lines = [line(1, 1, 0.40, 0), line(2, 1, 0.40, 0)]
    t = invoice_totals(lines)
    assert t["net_amount"] == 1 and abs(t["round_off"] - 0.20) < 1e-9


# ---------------------------------------------------------------- bills

def test_multi_line_invoice_net_adds_up(db, ids):
    bs = BillService()
    new = bs.add_invoice(ids["vendor"], "INV-1", "2026-05-10",
                         [line(ids["crp"], 3, 33.33, 5), line(ids["glucose"], 7, 12.37, 12)])
    rows = db.fetch_all("SELECT net_amount, round_off FROM bills WHERE id IN (?, ?) ORDER BY id", new)
    total = sum(r["net_amount"] for r in rows)
    assert abs(total - round(total)) < 1e-9, "invoice total must be whole rupees"
    assert rows[0]["round_off"] == 0, "round-off only on the last line"
    expected = invoice_totals([line(0, 3, 33.33, 5), line(0, 7, 12.37, 12)])["net_amount"]
    assert abs(total - expected) < 1e-9


def test_stock_received_on_invoice_date_and_linked(db, ids):
    b = BillService().add_bill(ids["crp"], ids["vendor"], "INV-2", "2026-05-10", "X", None, 20, 50, 12)
    row = db.fetch_one("SELECT * FROM stock_register WHERE bill_id = ?", (b,))
    assert row["date"] == "2026-05-10" and row["received_qty"] == 20 and row["txn_type"] == "PURCHASE"
    assert db.scalar("SELECT expiry_date FROM bills WHERE id = ?", (b,)) is None


def test_edit_and_delete_rebalance_invoice(db, ids):
    bs = BillService()
    a, b = bs.add_invoice(ids["vendor"], "INV-3", "2026-05-10",
                          [line(ids["crp"], 1, 0.40, 0), line(ids["glucose"], 1, 0.40, 0)])
    bs.update_bill(b, ids["glucose"], ids["vendor"], "INV-3", "2026-05-10", "", None, 1, 0.70, 0)
    total = db.scalar("SELECT SUM(net_amount) FROM bills WHERE invoice_number = 'INV-3'")
    assert total == 1.0  # 0.40 + 0.70 = 1.10 -> 1
    bs.delete_bill(b)
    assert db.scalar("SELECT net_amount FROM bills WHERE id = ?", (a,)) == 0.0  # 0.40 -> 0


def test_duplicate_invoice_detected_case_insensitive(db, ids):
    bs = BillService()
    bs.add_bill(ids["crp"], ids["vendor"], "RT/1184", "2026-05-10", "", None, 1, 1, 0)
    assert bs.invoice_exists(ids["vendor"], " rt/1184 ")
    assert not bs.invoice_exists(ids["vendor2"], "RT/1184")


def test_bill_edit_and_delete_protect_issued_stock(db, ids):
    bs, ss = BillService(), StockService()
    b = bs.add_bill(ids["crp"], ids["vendor"], "INV-4", "2026-05-10", "", None, 20, 50, 12)
    ss.issue_stock(ids["crp"], 15, issue_date="2026-05-20")
    with pytest.raises(StockError):
        bs.update_bill(b, ids["crp"], ids["vendor"], "INV-4", "2026-05-10", "", None, 10, 50, 12)
    with pytest.raises(StockError):
        bs.delete_bill(b)
    assert bs.get_bill_by_id(b)["quantity"] == 20 and ss.get_stock_balance(ids["crp"]) == 5
    bs.update_bill(b, ids["crp"], ids["vendor"], "INV-4A", "2026-05-08", "", None, 25, 40, 18, interstate=True)
    bill = bs.get_bill_by_id(b)
    assert bill["igst"] == 180 and bill["cgst"] == 0 and bill["net_amount"] == 1180
    assert db.scalar("SELECT COUNT(*) FROM stock_register WHERE bill_id = ?", (b,)) == 1
    assert ss.get_stock_balance(ids["crp"]) == 10


def test_changing_item_on_bill_moves_stock(db, ids):
    bs, ss = BillService(), StockService()
    b = bs.add_bill(ids["glucose"], ids["vendor"], "INV-5", "2026-06-01", "", None, 4, 10, 0)
    bs.update_bill(b, ids["hba1c"], ids["vendor"], "INV-5", "2026-06-01", "", None, 4, 10, 0)
    assert ss.get_stock_balance(ids["glucose"]) == 0 and ss.get_stock_balance(ids["hba1c"]) == 4


def test_invalid_invoice_rejected(db, ids):
    with pytest.raises(StockError):
        BillService().add_invoice(ids["vendor"], "   ", "2026-05-10", [line(ids["crp"], 1, 1)])
    with pytest.raises(StockError):
        BillService().add_invoice(ids["vendor"], "X", "2026-05-10", [line(ids["crp"], 0, 1)])
    assert db.scalar("SELECT COUNT(*) FROM bills") == 0


# ---------------------------------------------------------------- stock

def test_backdated_issue_refused(db, ids):
    ss = StockService()
    BillService().add_bill(ids["crp"], ids["vendor"], "I", "2026-05-10", "", None, 20, 1, 0)
    with pytest.raises(StockError):
        ss.issue_stock(ids["crp"], 5, issue_date="2026-05-01")
    ss.issue_stock(ids["crp"], 15, issue_date="2026-05-20", remarks="Ward")
    assert ss.get_stock_balance(ids["crp"]) == 5
    assert ss.get_stock_balance(ids["crp"], as_of="2026-05-15") == 20


def test_issue_edit_delete_and_ledger(db, ids):
    ss = StockService()
    BillService().add_bill(ids["crp"], ids["vendor"], "I", "2026-05-10", "", None, 20, 1, 0)
    iid = ss.issue_stock(ids["crp"], 2, issue_date="2026-06-10", remarks="Lab")
    ss.update_issue(iid, ids["crp"], 3, "2026-06-11", "OPD")
    assert ss.get_issue(iid)["issued_qty"] == 3
    with pytest.raises(StockError):
        ss.update_issue(iid, ids["crp"], 999, "2026-06-11")
    ledger = ss.item_ledger(ids["crp"])
    assert [r["balance"] for r in ledger] == [20, 17]
    assert ss.recent_remarks() == ["OPD"]
    ss.delete_issue(iid)
    assert ss.get_issue(iid) is None


def test_failed_transaction_leaves_no_partial_data(db, ids):
    n = db.scalar("SELECT COUNT(*) FROM bills")
    with pytest.raises(RuntimeError):
        with db.transaction():
            db.execute("INSERT INTO bills (vendor_id, invoice_number) VALUES (?, 'TMP')", (ids["vendor"],))
            raise RuntimeError("boom")
    assert db.scalar("SELECT COUNT(*) FROM bills") == n


# ---------------------------------------------------------------- masters & users

def test_master_names_unique_case_insensitive(db):
    from services.item_service import ItemService
    s = ItemService()
    with pytest.raises(MasterError):
        s.add("  glucose   KIT ")
    new = s.add("New  Reagent ")
    assert s.get(new)["name"] == "New Reagent"
    with pytest.raises(MasterError):
        s.rename(new, "crp")
    s.rename(new, "new reagent")  # same item, case change allowed
    s.delete(new)


def test_master_delete_blocked_when_used(db, ids):
    from services.vendor_service import VendorService
    BillService().add_bill(ids["crp"], ids["vendor"], "I", "2026-05-10", "", None, 1, 1, 0)
    with pytest.raises(MasterError):
        VendorService().delete(ids["vendor"])


def test_seed_runs_once(db):
    from models.seed_data import seed_if_first_run
    db.execute("DELETE FROM vendors WHERE name = 'JP ENTERPRISE'")
    assert seed_if_first_run(db) is False
    assert db.scalar("SELECT COUNT(*) FROM vendors WHERE name = 'JP ENTERPRISE'") == 0


def test_login_and_password_change(db):
    from services.user_service import UserService
    u = UserService()
    assert u.login(" ADMIN ", "admin") and u.is_default_password("admin")
    assert not u.login("admin", " admin ")  # passwords are exact (no trimming)
    with pytest.raises(ValueError):
        u.change_password("admin", "wrong", "newpass")
    with pytest.raises(ValueError):
        u.change_password("admin", "admin", "ab")
    u.change_password("admin", "admin", "s3cret pass")
    assert u.login("admin", "s3cret pass") and not u.login("admin", "admin")


# ---------------------------------------------------------------- reports

def test_reports(db, ids):
    from services.report_service import REPORTS, ReportService, run_report
    bs, ss = BillService(), StockService()
    bs.add_invoice(ids["vendor"], "A", "2026-04-15", [line(ids["crp"], 10, 100, 18)])
    bs.add_invoice(ids["vendor"], "B", "2026-05-03", [line(ids["crp"], 5, 100, 5), line(ids["glucose"], 2, 50, 0)])
    ss.issue_stock(ids["crp"], 4, issue_date="2026-05-20", remarks="Lab")

    st = ReportService().stock_statement("2026-05-01", "2026-05-31")
    crp = next(r for r in st.rows if r[0] == "CRP")
    assert crp == ("CRP", 10, 5, 4, 11)  # opening, received, issued, closing

    m = ReportService().purchases_by_period("2026-04-01", "2026-05-31", "month")
    assert [r[0] for r in m.rows] == ["2026-04", "2026-05"]
    assert m.rows[1][1] == 1 and m.rows[1][2] == 2  # 1 invoice, 2 lines
    assert m.totals[5] == 1180 + 625  # net: 1180 + (525 + 100)

    w = ReportService().purchases_by_period("2026-04-01", "2026-05-31", "week")
    assert w.rows[1][0] == "2026-04-27"  # Sunday 3 May belongs to week starting Monday 27 April

    g = ReportService().gst_summary("2026-04-01", "2026-05-31")
    assert {r[0]: r[2] for r in g.rows} == {0: 100, 5: 500, 18: 1000}

    c = ReportService().item_consumption("2026-05-01", "2026-05-31")
    assert c.rows == [("CRP", 4, 1, "2026-05-20", "2026-05-20")]

    for key, *_ in REPORTS:  # every report runs on an empty period too
        rows = run_report(key, "2020-01-01", "2020-01-31").rows
        if key == "stock_statement":  # lists every item, all zero
            assert len(rows) == 50 and all(r[1:] == (0, 0, 0, 0) for r in rows)
        else:
            assert rows == []

    d = ReportService().dashboard()
    assert d["items"] == 50


# ---------------------------------------------------------------- formatting

def test_indian_number_format():
    from utils.formatting import inr, format_cell
    assert inr(213994) == "₹2,13,994.00"
    assert inr(1234567.5, 0) == "₹12,34,568"
    assert inr(-950) == "-₹950.00"
    assert format_cell("2026-11", "month") == "Nov 2026"
    assert format_cell("Total", "money") == "Total"


def test_month_arithmetic():
    from datetime import date
    from ui.widgets import financial_year_start, months_before
    assert months_before(date(2026, 11, 1), 2) == date(2026, 9, 1)
    assert months_before(date(2026, 1, 1), 2) == date(2025, 11, 1)
    assert financial_year_start(date(2026, 3, 31)) == date(2025, 4, 1)
    assert financial_year_start(date(2026, 4, 1)) == date(2026, 4, 1)


# ---------------------------------------------------------------- migration of old databases

def _make_legacy_db(path):
    """A database exactly as the original (pre-2026-11) version created it."""
    c = sqlite3.connect(path)
    c.executescript("""
        CREATE TABLE users (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE NOT NULL,
                            password_hash TEXT NOT NULL);
        CREATE TABLE vendors (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE NOT NULL);
        CREATE TABLE items (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE NOT NULL);
        CREATE TABLE stock_register (id INTEGER PRIMARY KEY AUTOINCREMENT, item_id INTEGER NOT NULL,
            vendor_id INTEGER, received_qty INTEGER DEFAULT 0, issued_qty INTEGER DEFAULT 0,
            balance_qty INTEGER DEFAULT 0, date TEXT);
        CREATE TABLE bills (id INTEGER PRIMARY KEY AUTOINCREMENT, item_id INTEGER, vendor_id INTEGER NOT NULL,
            invoice_number TEXT, invoice_date TEXT, batch_number TEXT, expiry_date TEXT, quantity INTEGER,
            amount REAL, cgst REAL, sgst REAL, round_off REAL, net_amount REAL, entry_date TEXT);
        INSERT INTO vendors (name) VALUES ('OLD VENDOR');
        INSERT INTO items (name) VALUES ('Old Item'), ('Other Item');
        INSERT INTO bills VALUES (1, 1, 1, 'INV-1', '2026-03-01', 'B', '2027-01-01', 10, 1000, 90, 90, 0, 1180, '2026-11-19');
        INSERT INTO stock_register VALUES (1, 1, 1, 10, 0, 10, '2026-11-19');
        INSERT INTO bills VALUES (2, 2, 1, 'INV-2', '2026-03-02', 'B', '2027-01-01', 8, 800, 40, 40, 0, 880, '2026-11-19');
        INSERT INTO stock_register VALUES (2, 2, 1, 5, 0, 5, '2026-11-19');
        INSERT INTO stock_register VALUES (3, 2, 1, 3, 0, 3, '2026-11-19');
        INSERT INTO stock_register VALUES (4, 1, NULL, 0, 3, -3, '2026-03-05');
    """)
    c.commit()
    c.close()


def test_legacy_database_upgrade(data_dir):
    from models.migrations import LATEST_VERSION, get_version, migrate
    from services.db_service import get_db
    _make_legacy_db(data_dir / "hospital.db")
    d = get_db()
    assert get_version(d.conn) == 0
    migrate(d.conn)
    assert get_version(d.conn) == LATEST_VERSION
    assert d.scalar("SELECT bill_id FROM stock_register WHERE id = 1") == 1   # exact match linked
    assert d.scalar("SELECT COUNT(*) FROM stock_register WHERE bill_id = 2") == 0  # edited: not linked
    assert d.scalar("SELECT gst_rate FROM bills WHERE id = 1") == 18
    assert d.scalar("SELECT txn_type FROM stock_register WHERE id = 4") == "ISSUE"
    assert d.scalar("SELECT value FROM app_meta WHERE key = 'seeded'") == "1"

    # Editing the unlinked legacy bill corrects stock and links it
    ss, bs = StockService(), BillService()
    before = ss.get_stock_balance(2)
    bs.update_bill(2, 2, 1, "INV-2", "2026-03-02", "B", None, 6, 100, 5)
    assert ss.get_stock_balance(2) == before - 2
    assert d.scalar("SELECT COUNT(*) FROM stock_register WHERE bill_id = 2") == 1
    # Old version's date bug (issue before receipt) doesn't block fixing it
    bs.update_bill(1, 1, 1, "INV-1", "2026-03-01", "B", None, 10, 100, 18)
    assert ss.min_running_balance(1)[0] == 0
