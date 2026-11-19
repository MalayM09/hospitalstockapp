"""
Human-readable Excel exports.

A printout saved the hospital last time. These exports do the same job
automatically: plain Excel files that anyone can open without this app.

  * export_full_data()     - everything: stock summary, purchases, issues,
                             all stock movements, items, vendors
  * export_monthly_snapshot() - one month's stock statement (opening,
                             received, issued, closing) plus that month's
                             purchases and issues
"""
import calendar
import logging
from datetime import date, datetime
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

from services.db_service import get_db

log = logging.getLogger(__name__)

_HEADER_FONT = Font(bold=True, color="FFFFFF")
_HEADER_FILL = PatternFill("solid", fgColor="1565C0")
_TITLE_FONT = Font(bold=True, size=14)


def _write_sheet(wb, title, headers, rows, heading=None):
    ws = wb.create_sheet(title=title[:31])
    start = 1
    if heading:
        ws.cell(row=1, column=1, value=heading).font = _TITLE_FONT
        start = 3
    for col, h in enumerate(headers, 1):
        c = ws.cell(row=start, column=col, value=h)
        c.font = _HEADER_FONT
        c.fill = _HEADER_FILL
        c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    for r, row in enumerate(rows, start + 1):
        for col, value in enumerate(row, 1):
            ws.cell(row=r, column=col, value=value)
    # Column widths from content
    for col, h in enumerate(headers, 1):
        longest = max([len(str(h))] + [len(str(row[col - 1])) for row in rows if row[col - 1] is not None])
        ws.column_dimensions[get_column_letter(col)].width = min(max(10, longest + 2), 50)
    ws.freeze_panes = ws.cell(row=start + 1, column=1)
    return ws


def _save(wb, path):
    del wb["Sheet"]  # the empty default sheet
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    part = path.with_name(path.name + ".part.xlsx")
    wb.save(part)
    part.replace(path)
    return path


def _stock_summary(db, as_of=None):
    query = """
        SELECT i.name,
               COALESCE(SUM(s.received_qty), 0),
               COALESCE(SUM(s.issued_qty), 0),
               COALESCE(SUM(s.received_qty), 0) - COALESCE(SUM(s.issued_qty), 0)
        FROM items i
        LEFT JOIN stock_register s ON s.item_id = i.id {cond}
        GROUP BY i.id ORDER BY i.name
    """
    if as_of:
        return db.conn.execute(query.format(cond="AND s.date <= ?"), (as_of,)).fetchall()
    return db.conn.execute(query.format(cond="")).fetchall()


_PURCHASE_HEADERS = ["Bill ID", "Invoice Date", "Invoice No.", "Vendor", "Item", "Batch No.",
                     "Expiry", "Qty", "Taxable Amount", "GST %", "CGST", "SGST", "IGST",
                     "Round Off", "Net Amount", "Entered On"]

_PURCHASE_SQL = """
    SELECT b.id, COALESCE(b.invoice_date, b.entry_date), b.invoice_number, v.name, i.name,
           b.batch_number, b.expiry_date, b.quantity, b.amount, b.gst_rate, b.cgst, b.sgst,
           COALESCE(b.igst, 0), b.round_off, b.net_amount, b.entry_date
    FROM bills b JOIN vendors v ON v.id = b.vendor_id LEFT JOIN items i ON i.id = b.item_id
    {where}
    ORDER BY COALESCE(b.invoice_date, b.entry_date), b.id
"""

_ISSUE_HEADERS = ["Entry ID", "Date", "Item", "Qty Issued", "Remarks"]
_ISSUE_SQL = """
    SELECT s.id, s.date, i.name, s.issued_qty, COALESCE(s.remarks, '')
    FROM stock_register s JOIN items i ON i.id = s.item_id
    WHERE s.issued_qty > 0 {cond}
    ORDER BY s.date, s.id
"""


def export_full_data(path):
    """Write the complete database to one Excel workbook."""
    db = get_db()
    wb = Workbook()
    stamp = f"Generated {datetime.now():%d %b %Y %H:%M}"

    _write_sheet(wb, "Stock Summary", ["Item", "Total Received", "Total Issued", "Balance"],
                 _stock_summary(db), heading=f"Current Stock - {stamp}")
    _write_sheet(wb, "Purchases", _PURCHASE_HEADERS,
                 db.conn.execute(_PURCHASE_SQL.format(where="")).fetchall())
    _write_sheet(wb, "Issues", _ISSUE_HEADERS,
                 db.conn.execute(_ISSUE_SQL.format(cond="")).fetchall())
    _write_sheet(
        wb, "All Stock Movements",
        ["Entry ID", "Date", "Type", "Item", "Vendor", "Received", "Issued", "Bill ID", "Remarks"],
        db.conn.execute("""
            SELECT s.id, s.date, s.txn_type, i.name, v.name, s.received_qty, s.issued_qty,
                   s.bill_id, COALESCE(s.remarks, '')
            FROM stock_register s JOIN items i ON i.id = s.item_id
            LEFT JOIN vendors v ON v.id = s.vendor_id
            ORDER BY s.date, s.id
        """).fetchall(),
    )
    _write_sheet(wb, "Items", ["ID", "Name"],
                 db.conn.execute("SELECT id, name FROM items ORDER BY name").fetchall())
    _write_sheet(wb, "Vendors", ["ID", "Name"],
                 db.conn.execute("SELECT id, name FROM vendors ORDER BY name").fetchall())
    return _save(wb, path)


def export_monthly_snapshot(year, month, path):
    """Stock statement for one month plus that month's purchases and issues."""
    db = get_db()
    first = date(year, month, 1)
    last = date(year, month, calendar.monthrange(year, month)[1])
    f, l = first.isoformat(), last.isoformat()
    month_name = first.strftime("%B %Y")

    rows = db.conn.execute("""
        SELECT i.name,
               COALESCE(SUM(CASE WHEN s.date < ? THEN COALESCE(s.received_qty,0) - COALESCE(s.issued_qty,0) END), 0),
               COALESCE(SUM(CASE WHEN s.date BETWEEN ? AND ? THEN s.received_qty END), 0),
               COALESCE(SUM(CASE WHEN s.date BETWEEN ? AND ? THEN s.issued_qty END), 0),
               COALESCE(SUM(CASE WHEN s.date <= ? THEN COALESCE(s.received_qty,0) - COALESCE(s.issued_qty,0) END), 0)
        FROM items i LEFT JOIN stock_register s ON s.item_id = i.id
        GROUP BY i.id ORDER BY i.name
    """, (f, f, l, f, l, l)).fetchall()

    wb = Workbook()
    _write_sheet(wb, "Stock Statement",
                 ["Item", "Opening Balance", "Received", "Issued", "Closing Balance"], rows,
                 heading=f"Stock Statement - {month_name} (generated {datetime.now():%d %b %Y})")
    _write_sheet(wb, "Purchases", _PURCHASE_HEADERS,
                 db.conn.execute(_PURCHASE_SQL.format(
                     where="WHERE COALESCE(b.invoice_date, b.entry_date) BETWEEN ? AND ?"), (f, l)).fetchall(),
                 heading=f"Purchases - {month_name}")
    _write_sheet(wb, "Issues", _ISSUE_HEADERS,
                 db.conn.execute(_ISSUE_SQL.format(cond="AND s.date BETWEEN ? AND ?"), (f, l)).fetchall(),
                 heading=f"Issues - {month_name}")
    return _save(wb, path)


def write_exports_to_destination(folder):
    """
    Called by the daily backup for each destination folder:
      - Full_Data_Latest.xlsx (overwritten every day)
      - Monthly Snapshots/Stock_Snapshot_YYYY-MM.xlsx for last month, if missing
    """
    folder = Path(folder)
    export_full_data(folder / "Full_Data_Latest.xlsx")

    today = date.today()
    year, month = (today.year, today.month - 1) if today.month > 1 else (today.year - 1, 12)
    snap = folder / "Monthly Snapshots" / f"Stock_Snapshot_{year}-{month:02d}.xlsx"
    if not snap.exists():
        export_monthly_snapshot(year, month, snap)
        log.info("Wrote monthly snapshot %s", snap)
