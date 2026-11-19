"""
Headless run through every screen: sign in, purchase, issue, registers, edits,
masters, reports, backup, printing HTML, large text, log out.
"""
import pytest
from PyQt6.QtCore import QDate

import ui.backup_ui
import ui.pages.backup
import ui.pages.masters
import ui.pages.purchase
import ui.pages.registers


@pytest.fixture
def ui_env(db, qapp, monkeypatch):
    """Theme + scheduler, with confirmations auto-accepted and alerts recorded."""
    from services.backup_scheduler import BackupScheduler
    from ui.theme import apply_theme
    alerts = []
    for mod in (ui.pages.purchase, ui.pages.registers, ui.pages.masters, ui.pages.backup, ui.backup_ui):
        if hasattr(mod, "confirm"):
            monkeypatch.setattr(mod, "confirm", lambda *a, **k: True)
        if hasattr(mod, "alert"):
            monkeypatch.setattr(mod, "alert", lambda parent, title, text, *a: alerts.append((title, text)))
    apply_theme(qapp)
    sched = BackupScheduler(db)
    yield {"alerts": alerts, "sched": sched}
    sched.timer.stop()


def make_main(qapp):
    from ui.main_window import MainWindow
    w = MainWindow("admin")
    w.resize(1366, 698)
    w.show()
    qapp.processEvents()
    return w


def test_login_goes_straight_in(ui_env, qapp):
    from ui.login_window import LoginWindow
    win = LoginWindow()
    got = []
    win.logged_in.connect(got.append)
    win.username.setText("admin")
    win.password.setText("wrong")
    win.attempt()
    assert got == [] and "Incorrect" in win.error.text()
    win.password.setText("admin")
    win.attempt()
    assert got == ["admin"] and win.error.text() == ""


def test_every_page_opens(ui_env, qapp):
    from ui.main_window import NAV
    w = make_main(qapp)
    for _, entries in NAV:
        for key, *_ in entries:
            w.navigate(key)
            qapp.processEvents()
            assert w.current.nav_key == key
    w.close()


def test_purchase_issue_and_registers_flow(ui_env, qapp, db, ids):
    w = make_main(qapp)
    w.navigate("purchase")
    p = w.current
    p.vendor.set_current_id(ids["vendor"])
    p.invoice_no.setText("RT/1")
    p.invoice_date.setDate(QDate(2026, 5, 1))
    for item, q, rate in [(ids["crp"], "10", "100"), (ids["glucose"], "5", "33.33")]:
        p.item.set_current_id(item)
        p.qty.setText(q)
        p.rate.setText(rate)
        assert p.add_line()
    assert len(p.lines) == 2 and p.table.model.rowCount() == 2
    assert p.net.text() == "₹1,377"  # 1180 + 196.65 = 1376.65 -> 1377
    p.on_save()
    assert db.scalar("SELECT COUNT(*) FROM bills WHERE invoice_number = 'RT/1'") == 2
    assert db.scalar("SELECT SUM(net_amount) FROM bills") == 1377
    assert p.lines == [] and p.vendor.current_id() is None  # form cleared for the next invoice

    # validation is inline, nothing saved
    p.vendor.set_current_id(ids["vendor"])
    p.invoice_no.setText("RT/2")
    p.item.set_current_id(ids["crp"])
    p.qty.setText("abc")
    p.on_save()
    assert p.f_qty.error.isVisibleTo(p) and db.scalar("SELECT COUNT(*) FROM bills") == 2
    p._reset(keep_date=True)

    # typing a new vendor name offers to add it (auto-confirmed here)
    p.vendor.setEditText("Brand New Supplier")
    p.invoice_no.setText("BN/1")
    p.invoice_date.setDate(QDate(2026, 5, 2))
    p.item.set_current_id(ids["crp"])
    p.qty.setText("2")
    p.rate.setText("10")
    p.on_save()
    assert db.scalar("SELECT COUNT(*) FROM vendors WHERE name = 'Brand New Supplier'") == 1

    # issue: before the purchase date is refused inline, after is fine
    w.navigate("issue")
    iss = w.current
    iss.item.set_current_id(ids["crp"])
    iss.date.setDate(QDate(2026, 4, 1))
    iss.qty.setText("3")
    iss.on_save()
    assert iss.f_qty.error.isVisibleTo(iss)
    iss.date.setDate(QDate(2026, 5, 5))
    iss.remarks.setCurrentText("Ward 2")
    iss.qty.setText("3")
    iss.on_save()
    assert StockBalance(db, ids["crp"]) == 9
    assert iss.date.date() == QDate(2026, 5, 5) and iss.remarks.currentText() == "Ward 2"

    # stock register: filters and ledger data
    w.navigate("stock")
    sr = w.current
    sr._set_status("in")
    names = [r[0] for r in sr.table.visible_rows()]
    assert names == ["CRP", "Glucose Kit"]
    sr._set_status("all")
    sr.search.setText("glu")
    assert [r[0] for r in sr.table.visible_rows()] == ["Glucose Kit"]
    sr.search.clear()

    # issue register: range + delete
    w.navigate("issues")
    ir = w.current
    ir.range.quick.setCurrentText("All time")
    assert len(ir.table.visible_rows()) == 1
    ir.table.view.selectRow(0)
    ir.delete_selected()
    assert db.scalar("SELECT COUNT(*) FROM stock_register WHERE issued_qty > 0") == 0

    # bills: totals footer and deleting a line rebalances the invoice
    w.navigate("bills")
    b = w.current
    b.range.quick.setCurrentText("All time")
    assert len(b.table.visible_rows()) == 3
    assert "Net: ₹1,401.00" in b.footer.text()  # 1377 + 24 (₹20 + 18% GST, rounded)
    rep = b.current_report()
    assert rep.totals[10] == 1401
    w.close()


def StockBalance(db, item_id):
    from services.stock_service import StockService
    return StockService().get_stock_balance(item_id)


def test_dialogs(ui_env, qapp, db, ids):
    from services.bill_service import BillService
    from services.stock_service import StockService
    from ui.dialogs import ChangePasswordDialog, EditBillDialog, EditIssueDialog, ItemLedgerDialog
    bill = BillService().add_bill(ids["crp"], ids["vendor"], "E/1", "2026-05-01", "", None, 10, 100, 18)
    iid = StockService().issue_stock(ids["crp"], 4, issue_date="2026-05-03")

    d = EditBillDialog(bill)
    d.qty.setText("2")  # below the 4 already issued -> refused with message
    assert d.save() is False and d.error.isVisibleTo(d)
    d.qty.setText("12")
    assert "₹1,416.00" in d.totals.text()
    assert d.save() is True and BillService().get_bill_by_id(bill)["quantity"] == 12

    e = EditIssueDialog(iid)
    e.qty.setText("5")
    assert e.save() and StockService().get_issue(iid)["issued_qty"] == 5

    ItemLedgerDialog(ids["crp"])  # builds without error
    c = ChangePasswordDialog("admin")
    c.current.setText("admin")
    c.new.setText("pass1")
    c.repeat.setText("pass2")
    assert c.save() is False
    c.repeat.setText("pass1")
    assert c.save() is True


def test_masters_reports_backup(ui_env, qapp, db, ids, tmp_path):
    w = make_main(qapp)
    w.navigate("items")
    items = w.current
    assert len(items.table.visible_rows()) == 50
    items.service.add("Zinc reagent")
    items.refresh()
    assert len(items.table.visible_rows()) == 51

    w.navigate("reports")
    r = w.current
    for i in range(r.list.count()):
        r.list.setCurrentRow(i)
        qapp.processEvents()
        assert r.report is not None and r.table is not None

    from ui.printing import build_html
    html = build_html("T", ["Item", "Qty"], [("A & B <x>", "1")], ["text", "int"])
    assert "A &amp; B &lt;x&gt;" in html

    w.navigate("backup")
    bp = w.current
    off = tmp_path / "pendrive"
    off.mkdir()
    bp._add_destination(str(off))
    bp.backup_now()
    assert (off / "HospitalStockBackups").exists()
    assert (off / "HospitalStockBackups" / "Full_Data_Latest.xlsx").exists()
    bp.list.refresh()
    assert bp.list.selected() is not None

    w.toggle_large_text(True)
    assert w.current.nav_key == "backup"
    w.toggle_large_text(False)
    w.close()


def test_data_change_refreshes_visible_page(ui_env, qapp, db, ids):
    from services.bill_service import BillService
    w = make_main(qapp)
    w.navigate("dashboard")
    before = w.current.k_purchase.value.text()
    from datetime import date
    BillService().add_bill(ids["crp"], ids["vendor"], "D/1", date.today().isoformat(), "", None, 1, 500, 0)
    qapp.processEvents()
    assert w.current.k_purchase.value.text() != before == "₹0"
    w.close()
