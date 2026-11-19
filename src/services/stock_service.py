"""
Stock register operations.

Every stock movement is a row in `stock_register`:
    received_qty > 0  -> stock in  (OPENING, PURCHASE, ADJUSTMENT)
    issued_qty   > 0  -> stock out (ISSUE)
Balance of an item = SUM(received_qty) - SUM(issued_qty).

Note: the old `balance_qty` column holds only that row's +/- change, not a
running balance. It is kept for compatibility but never used for calculations.

Changes are checked so that an item's balance never drops below zero on any
date - e.g. you can't issue stock on 3 May that only arrived on 10 May, and you
can't delete a bill whose stock has already been issued.
"""
from contextlib import contextmanager
from datetime import date as _date, datetime

from services.db_service import get_db


# Items at or below this balance are shown as "Low". (Per-item minimum levels
# can replace this later.)
LOW_STOCK_LEVEL = 10


class StockError(ValueError):
    """A stock change that was refused, with a message suitable for the user."""


def stock_status(balance):
    """'out', 'low' or 'ok' for a balance."""
    if balance <= 0:
        return "out"
    if balance <= LOW_STOCK_LEVEL:
        return "low"
    return "ok"


def _today():
    return _date.today().isoformat()


def _now():
    return datetime.now().isoformat(timespec="seconds")


class StockService:
    def __init__(self):
        self.db = get_db()

    # ---- lookups -------------------------------------------------------------

    def _item_name(self, item_id):
        return self.db.scalar("SELECT name FROM items WHERE id = ?", (item_id,)) or f"item #{item_id}"

    # ---- negative-stock protection ------------------------------------------

    def min_running_balance(self, item_id):
        """
        Lowest balance the item reaches on any date, and the first date it hits it.
        Returns (min_balance, date). An item with no history returns (0, None).
        """
        rows = self.db.fetch_all("""
            SELECT date, SUM(COALESCE(received_qty, 0) - COALESCE(issued_qty, 0)) AS net
            FROM stock_register WHERE item_id = ?
            GROUP BY date ORDER BY date
        """, (item_id,))
        balance = 0
        lowest, lowest_date = 0, None
        for r in rows:
            balance += r["net"]
            if balance < lowest:
                lowest, lowest_date = balance, r["date"]
        return lowest, lowest_date

    @contextmanager
    def guard_negative_stock(self, item_ids):
        """
        Use inside a transaction around stock changes. If the changes make any
        item's balance go negative on some date (and it wasn't already that bad
        before), a StockError is raised and the transaction is rolled back.
        """
        item_ids = {i for i in item_ids if i}
        before = {i: self.min_running_balance(i)[0] for i in item_ids}
        yield
        for item_id in item_ids:
            after, when = self.min_running_balance(item_id)
            if after < 0 and after < before[item_id]:
                raise StockError(
                    f"This change would make the stock of '{self._item_name(item_id)}' "
                    f"go negative ({after}) on {when or 'an undated entry'}.\n\n"
                    f"Stock cannot be issued before it is received, and a purchase "
                    f"cannot be removed after its stock has been issued."
                )

    # ---- stock in --------------------------------------------------------------

    def receive_stock(self, item_id, vendor_id, qty, date=None, bill_id=None,
                      txn_type="PURCHASE", remarks=""):
        """Record stock received. `date` is when the stock actually arrived (YYYY-MM-DD)."""
        return self.db.execute("""
            INSERT INTO stock_register
                (item_id, vendor_id, received_qty, issued_qty, balance_qty, date,
                 txn_type, bill_id, remarks, created_at)
            VALUES (?, ?, ?, 0, ?, ?, ?, ?, ?, ?)
        """, (item_id, vendor_id, qty, qty, date or _today(), txn_type, bill_id, remarks, _now()))

    # ---- stock out -------------------------------------------------------------

    def issue_stock(self, item_id, qty, vendor_id=None, remarks="", issue_date=None):
        """Record stock issued for use. Refused if it would make stock negative."""
        if qty <= 0:
            raise StockError("Quantity must be more than zero.")
        with self.db.transaction(), self.guard_negative_stock([item_id]):
            return self.db.execute("""
                INSERT INTO stock_register
                    (item_id, vendor_id, received_qty, issued_qty, balance_qty, date,
                     txn_type, remarks, created_at)
                VALUES (?, ?, 0, ?, ?, ?, 'ISSUE', ?, ?)
            """, (item_id, vendor_id, qty, -qty, issue_date or _today(), remarks, _now()))

    def get_issue(self, stock_id):
        return self.db.fetch_one("""
            SELECT s.*, i.name AS item_name FROM stock_register s
            JOIN items i ON s.item_id = i.id
            WHERE s.id = ? AND s.issued_qty > 0
        """, (stock_id,))

    def update_issue(self, stock_id, item_id, qty, issue_date, remarks=""):
        """Correct an issue entry (item, quantity, date or remarks)."""
        old = self.get_issue(stock_id)
        if not old:
            raise StockError("That issue entry no longer exists.")
        if qty <= 0:
            raise StockError("Quantity must be more than zero.")
        with self.db.transaction(), self.guard_negative_stock([old["item_id"], item_id]):
            self.db.execute("""
                UPDATE stock_register
                SET item_id = ?, issued_qty = ?, balance_qty = ?, date = ?, remarks = ?
                WHERE id = ?
            """, (item_id, qty, -qty, issue_date, remarks, stock_id))

    def delete_issue(self, stock_id):
        """Delete an issue entry (puts the stock back)."""
        if not self.get_issue(stock_id):
            raise StockError("That issue entry no longer exists.")
        self.db.execute("DELETE FROM stock_register WHERE id = ? AND issued_qty > 0", (stock_id,))

    # ---- views ---------------------------------------------------------------

    def get_stock_issuance_history(self, start_date=None, end_date=None, search_term=None):
        query = """
            SELECT s.id AS sr_no, s.date, i.name AS item_name, s.issued_qty,
                   COALESCE(s.remarks, '') AS remarks
            FROM stock_register s
            JOIN items i ON s.item_id = i.id
            WHERE s.issued_qty > 0
        """
        params = []
        if start_date:
            query += " AND s.date >= ?"
            params.append(start_date)
        if end_date:
            query += " AND s.date <= ?"
            params.append(end_date)
        if search_term:
            query += " AND LOWER(i.name) LIKE ?"
            params.append(f"%{search_term.lower()}%")
        query += " ORDER BY s.date DESC, s.id DESC"
        return self.db.fetch_all(query, params)

    def get_stock_balance(self, item_id, as_of=None):
        """Balance of an item now, or at the end of date `as_of` (YYYY-MM-DD)."""
        query = """
            SELECT COALESCE(SUM(received_qty), 0) - COALESCE(SUM(issued_qty), 0)
            FROM stock_register WHERE item_id = ?
        """
        params = [item_id]
        if as_of:
            query += " AND date <= ?"
            params.append(as_of)
        return self.db.scalar(query, params) or 0

    def get_recent_issues(self, limit=50):
        return self.db.fetch_all("""
            SELECT s.id, s.date, i.name AS item_name, s.issued_qty, s.remarks
            FROM stock_register s JOIN items i ON s.item_id = i.id
            WHERE s.issued_qty > 0
            ORDER BY s.id DESC LIMIT ?
        """, (limit,))

    def get_stock_register_view(self):
        """Current stock per item: id, name, received, issued, balance."""
        return self.db.fetch_all("""
            SELECT i.id, i.name,
                   COALESCE(SUM(s.received_qty), 0) AS received,
                   COALESCE(SUM(s.issued_qty), 0) AS issued,
                   COALESCE(SUM(s.received_qty), 0) - COALESCE(SUM(s.issued_qty), 0) AS balance
            FROM items i
            LEFT JOIN stock_register s ON i.id = s.item_id
            GROUP BY i.id, i.name
            ORDER BY i.name COLLATE NOCASE
        """)

    def item_ledger(self, item_id):
        """Every movement of one item, oldest first, with a running balance."""
        rows = self.db.fetch_all("""
            SELECT s.id, s.date, s.txn_type, COALESCE(v.name, '') AS vendor,
                   COALESCE(s.remarks, '') AS remarks,
                   COALESCE(s.received_qty, 0) AS qty_in, COALESCE(s.issued_qty, 0) AS qty_out
            FROM stock_register s LEFT JOIN vendors v ON v.id = s.vendor_id
            WHERE s.item_id = ?
            ORDER BY s.date, s.id
        """, (item_id,))
        balance = 0
        for r in rows:
            balance += r["qty_in"] - r["qty_out"]
            r["balance"] = balance
        return rows

    def recent_remarks(self, limit=15):
        """Most used 'issued to / remarks' values, for suggestions."""
        rows = self.db.fetch_all("""
            SELECT remarks FROM stock_register
            WHERE issued_qty > 0 AND TRIM(COALESCE(remarks, '')) != ''
            GROUP BY remarks ORDER BY COUNT(*) DESC LIMIT ?
        """, (limit,))
        return [r["remarks"] for r in rows]
