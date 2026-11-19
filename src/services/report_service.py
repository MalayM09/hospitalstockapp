"""
Reports and dashboard figures.

Every report returns a Report: column definitions, rows and an optional totals
row, so the screen, Excel export and print all show exactly the same thing.
All dates are invoice dates (purchases) or issue dates (issues).
"""
from dataclasses import dataclass, field
from datetime import date

from services.db_service import get_db
from services.stock_service import LOW_STOCK_LEVEL

# Column kinds: text, int, money, date, pct
@dataclass
class Report:
    title: str
    columns: list                 # [(header, kind)]
    rows: list                    # [tuple]
    totals: tuple = None          # same length as columns, or None
    note: str = ""
    period: str = ""
    extra: dict = field(default_factory=dict)


_BILL_DATE = "COALESCE(b.invoice_date, b.entry_date)"


def _period_text(start, end):
    fmt = lambda d: date.fromisoformat(d).strftime("%d %b %Y")
    return f"{fmt(start)} to {fmt(end)}"


def _sum(rows, idx):
    return round(sum((r[idx] or 0) for r in rows), 2)


class ReportService:
    def __init__(self):
        self.db = get_db()

    # ---- dashboard -------------------------------------------------------------

    def dashboard(self, today=None):
        today = today or date.today()
        month_start = today.replace(day=1).isoformat()
        t = today.isoformat()
        q = self.db.scalar
        balances = self.db.fetch_all("""
            SELECT i.id, i.name, COALESCE(SUM(s.received_qty), 0) - COALESCE(SUM(s.issued_qty), 0) AS balance
            FROM items i LEFT JOIN stock_register s ON s.item_id = i.id
            GROUP BY i.id ORDER BY balance, i.name COLLATE NOCASE
        """)
        low = [b for b in balances if b["balance"] <= LOW_STOCK_LEVEL]
        recent = self.db.fetch_all("""
            SELECT s.date, s.txn_type, i.name AS item, COALESCE(s.received_qty, 0) AS qty_in,
                   COALESCE(s.issued_qty, 0) AS qty_out, COALESCE(v.name, '') AS vendor,
                   COALESCE(s.remarks, '') AS remarks
            FROM stock_register s JOIN items i ON i.id = s.item_id
            LEFT JOIN vendors v ON v.id = s.vendor_id
            ORDER BY s.id DESC LIMIT 12
        """)
        return {
            "items": len(balances),
            "low": low,
            "out_count": sum(1 for b in low if b["balance"] <= 0),
            "purchase_total": q(f"SELECT COALESCE(SUM(net_amount), 0) FROM bills b "
                                f"WHERE {_BILL_DATE} BETWEEN ? AND ?", (month_start, t)),
            "invoice_count": q(f"SELECT COUNT(DISTINCT vendor_id || '|' || invoice_number) FROM bills b "
                               f"WHERE {_BILL_DATE} BETWEEN ? AND ?", (month_start, t)),
            "issued_units": q("SELECT COALESCE(SUM(issued_qty), 0) FROM stock_register "
                              "WHERE issued_qty > 0 AND date BETWEEN ? AND ?", (month_start, t)),
            "issue_count": q("SELECT COUNT(*) FROM stock_register WHERE issued_qty > 0 "
                             "AND date BETWEEN ? AND ?", (month_start, t)),
            "recent": recent,
        }

    # ---- reports ---------------------------------------------------------------

    def stock_statement(self, start, end):
        """Opening, received, issued and closing balance per item for a period."""
        rows = self.db.conn.execute("""
            SELECT i.name,
                   COALESCE(SUM(CASE WHEN s.date < ? THEN COALESCE(s.received_qty,0) - COALESCE(s.issued_qty,0) END), 0),
                   COALESCE(SUM(CASE WHEN s.date BETWEEN ? AND ? THEN s.received_qty END), 0),
                   COALESCE(SUM(CASE WHEN s.date BETWEEN ? AND ? THEN s.issued_qty END), 0),
                   COALESCE(SUM(CASE WHEN s.date <= ? THEN COALESCE(s.received_qty,0) - COALESCE(s.issued_qty,0) END), 0)
            FROM items i LEFT JOIN stock_register s ON s.item_id = i.id
            GROUP BY i.id ORDER BY i.name COLLATE NOCASE
        """, (start, start, end, start, end, end)).fetchall()
        rows = [tuple(r) for r in rows]
        return Report(
            "Stock Statement",
            [("Item", "text"), ("Opening", "int"), ("Received", "int"), ("Issued", "int"), ("Closing", "int")],
            rows, ("Total", _sum(rows, 1), _sum(rows, 2), _sum(rows, 3), _sum(rows, 4)),
            period=_period_text(start, end),
            note="Opening = balance before the start date; Closing = balance at the end date.",
        )

    def purchases_by_period(self, start, end, period="month"):
        """Purchase totals grouped by day, week (starting Monday) or month."""
        group, label, title = {
            "day": (_BILL_DATE, "Date", "Purchases by Day"),
            "week": (f"date({_BILL_DATE}, '-6 days', 'weekday 1')", "Week starting", "Purchases by Week"),
            "month": (f"strftime('%Y-%m', {_BILL_DATE})", "Month", "Purchases by Month"),
        }[period]
        rows = self.db.conn.execute(f"""
            SELECT {group} AS p,
                   COUNT(DISTINCT b.vendor_id || '|' || b.invoice_number),
                   COUNT(*),
                   ROUND(SUM(b.amount), 2),
                   ROUND(SUM(COALESCE(b.cgst,0) + COALESCE(b.sgst,0) + COALESCE(b.igst,0)), 2),
                   ROUND(SUM(b.net_amount), 2)
            FROM bills b WHERE {_BILL_DATE} BETWEEN ? AND ?
            GROUP BY p ORDER BY p
        """, (start, end)).fetchall()
        kind = "month" if period == "month" else "date"
        rows = [tuple(r) for r in rows]
        return Report(
            title,
            [(label, kind), ("Invoices", "int"), ("Item lines", "int"), ("Taxable value", "money"),
             ("GST", "money"), ("Net amount", "money")],
            rows, ("Total", _sum(rows, 1), _sum(rows, 2), _sum(rows, 3), _sum(rows, 4), _sum(rows, 5)),
            period=_period_text(start, end),
        )

    def vendor_purchases(self, start, end):
        rows = self.db.conn.execute(f"""
            SELECT v.name,
                   COUNT(DISTINCT b.invoice_number),
                   COUNT(*),
                   ROUND(SUM(b.amount), 2),
                   ROUND(SUM(COALESCE(b.cgst,0) + COALESCE(b.sgst,0) + COALESCE(b.igst,0)), 2),
                   ROUND(SUM(b.net_amount), 2)
            FROM bills b JOIN vendors v ON v.id = b.vendor_id
            WHERE {_BILL_DATE} BETWEEN ? AND ?
            GROUP BY v.id ORDER BY SUM(b.net_amount) DESC
        """, (start, end)).fetchall()
        rows = [tuple(r) for r in rows]
        return Report(
            "Vendor-wise Purchases",
            [("Vendor", "text"), ("Invoices", "int"), ("Item lines", "int"), ("Taxable value", "money"),
             ("GST", "money"), ("Net amount", "money")],
            rows, ("Total", _sum(rows, 1), _sum(rows, 2), _sum(rows, 3), _sum(rows, 4), _sum(rows, 5)),
            period=_period_text(start, end),
        )

    def item_consumption(self, start, end):
        """How much of each item was issued in the period (items with issues only)."""
        rows = self.db.conn.execute("""
            SELECT i.name, SUM(s.issued_qty), COUNT(*), MIN(s.date), MAX(s.date)
            FROM stock_register s JOIN items i ON i.id = s.item_id
            WHERE s.issued_qty > 0 AND s.date BETWEEN ? AND ?
            GROUP BY i.id ORDER BY SUM(s.issued_qty) DESC, i.name
        """, (start, end)).fetchall()
        rows = [tuple(r) for r in rows]
        return Report(
            "Item Consumption",
            [("Item", "text"), ("Units issued", "int"), ("Issue entries", "int"),
             ("First issue", "date"), ("Last issue", "date")],
            rows, ("Total", _sum(rows, 1), _sum(rows, 2), "", ""),
            period=_period_text(start, end),
        )

    def gst_summary(self, start, end):
        """Taxable value and tax by GST rate (for accounts)."""
        rows = self.db.conn.execute(f"""
            SELECT COALESCE(b.gst_rate, 0),
                   COUNT(*),
                   ROUND(SUM(b.amount), 2), ROUND(SUM(COALESCE(b.cgst,0)), 2),
                   ROUND(SUM(COALESCE(b.sgst,0)), 2), ROUND(SUM(COALESCE(b.igst,0)), 2),
                   ROUND(SUM(b.amount + COALESCE(b.cgst,0) + COALESCE(b.sgst,0) + COALESCE(b.igst,0)), 2)
            FROM bills b WHERE {_BILL_DATE} BETWEEN ? AND ?
            GROUP BY COALESCE(b.gst_rate, 0) ORDER BY 1
        """, (start, end)).fetchall()
        rows = [tuple(r) for r in rows]
        return Report(
            "GST Summary",
            [("GST rate", "pct"), ("Item lines", "int"), ("Taxable value", "money"), ("CGST", "money"),
             ("SGST", "money"), ("IGST", "money"), ("Total (before round-off)", "money")],
            rows, ("Total", _sum(rows, 1), _sum(rows, 2), _sum(rows, 3), _sum(rows, 4), _sum(rows, 5), _sum(rows, 6)),
            period=_period_text(start, end),
        )


REPORTS = [
    ("stock_statement", "Stock statement", "Opening, received, issued, closing per item"),
    ("purchases_month", "Purchases by month", "Spending per month"),
    ("purchases_week", "Purchases by week", "Spending per week (Mon–Sun)"),
    ("purchases_day", "Purchases by day", "Spending per day"),
    ("vendor_purchases", "Vendor-wise purchases", "Spending per vendor"),
    ("item_consumption", "Item consumption", "Units issued per item"),
    ("gst_summary", "GST summary", "Tax by GST rate"),
]


def run_report(key, start, end):
    svc = ReportService()
    if key.startswith("purchases_"):
        return svc.purchases_by_period(start, end, key.split("_", 1)[1])
    return getattr(svc, key)(start, end)
