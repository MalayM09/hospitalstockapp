"""
Purchase bills.

Each bill creates one linked PURCHASE row in the stock register, dated on the
invoice date. Adding, editing and deleting a bill always happens in a single
transaction together with its stock row, and is refused if it would make stock
negative (e.g. deleting a purchase whose stock has already been issued).
"""
from datetime import date as _date, datetime

from services.db_service import get_db
from services.gst import compute_totals
from services.stock_service import StockService, StockError


def _now():
    return datetime.now().isoformat(timespec="seconds")


class BillService:
    def __init__(self):
        self.db = get_db()
        self.stock_service = StockService()

    def add_bill(self, item_id, vendor_id, invoice_number, invoice_date, batch_number,
                 expiry_date, quantity, rate, gst_rate, interstate=False):
        """
        Save a purchase and receive its stock on the invoice date.
        Taxes and net amount are calculated here from quantity x rate and GST %.
        Returns the new bill id.
        """
        if not item_id or not vendor_id:
            raise StockError("Please select both an item and a vendor.")
        if quantity <= 0:
            raise StockError("Quantity must be more than zero.")
        t = compute_totals(quantity, rate, gst_rate, interstate)
        now = _now()

        with self.db.transaction():
            bill_id = self.db.execute("""
                INSERT INTO bills (
                    item_id, vendor_id, invoice_number, invoice_date, batch_number,
                    expiry_date, quantity, amount, cgst, sgst, igst, gst_rate,
                    round_off, net_amount, entry_date, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                item_id, vendor_id, invoice_number, invoice_date, batch_number,
                expiry_date, quantity, t["amount"], t["cgst"], t["sgst"], t["igst"], gst_rate,
                t["round_off"], t["net_amount"], _date.today().isoformat(), now, now,
            ))
            self.stock_service.receive_stock(
                item_id, vendor_id, quantity, date=invoice_date, bill_id=bill_id,
                txn_type="PURCHASE", remarks=f"Invoice {invoice_number}",
            )
        return bill_id

    def get_recent_bills(self, limit=20):
        return self.db.fetch_all("""
            SELECT b.id, b.entry_date, b.invoice_date, v.name AS vendor, i.name AS item_name,
                   b.invoice_number, b.quantity, b.net_amount
            FROM bills b
            JOIN vendors v ON b.vendor_id = v.id
            LEFT JOIN items i ON b.item_id = i.id
            ORDER BY b.id DESC
            LIMIT ?
        """, (limit,))

    def get_bill_by_id(self, bill_id):
        return self.db.fetch_one("""
            SELECT b.*, v.name AS vendor_name, i.name AS item_name
            FROM bills b
            JOIN vendors v ON b.vendor_id = v.id
            LEFT JOIN items i ON b.item_id = i.id
            WHERE b.id = ?
        """, (bill_id,))

    def _remove_bill_stock(self, bill):
        """Take back the stock a bill added (inside a transaction)."""
        linked = self.db.scalar("SELECT COUNT(*) FROM stock_register WHERE bill_id = ?", (bill["id"],))
        if linked:
            self.db.execute("DELETE FROM stock_register WHERE bill_id = ?", (bill["id"],))
        elif bill["item_id"] and (bill["quantity"] or 0) > 0:
            # Bill saved by an older version without a link to its stock row:
            # offset it on the date the old version recorded the receipt.
            self.stock_service.receive_stock(
                bill["item_id"], bill["vendor_id"], -bill["quantity"],
                date=bill["entry_date"] or bill["invoice_date"],
                txn_type="ADJUSTMENT",
                remarks=f"Reversal of bill #{bill['id']} (invoice {bill['invoice_number']})",
            )

    def update_bill(self, bill_id, item_id, vendor_id, invoice_number, invoice_date,
                    batch_number, expiry_date, quantity, rate, gst_rate, interstate=False):
        """Edit a bill; its stock row and taxes are recalculated to match."""
        old = self.get_bill_by_id(bill_id)
        if not old:
            raise StockError("That bill no longer exists.")
        if not item_id or not vendor_id:
            raise StockError("Please select both an item and a vendor.")
        if quantity <= 0:
            raise StockError("Quantity must be more than zero.")
        t = compute_totals(quantity, rate, gst_rate, interstate)

        with self.db.transaction(), \
                self.stock_service.guard_negative_stock([old["item_id"], item_id]):
            self._remove_bill_stock(old)
            self.db.execute("""
                UPDATE bills SET
                    item_id = ?, vendor_id = ?, invoice_number = ?, invoice_date = ?,
                    batch_number = ?, expiry_date = ?, quantity = ?, amount = ?,
                    cgst = ?, sgst = ?, igst = ?, gst_rate = ?, round_off = ?,
                    net_amount = ?, updated_at = ?
                WHERE id = ?
            """, (
                item_id, vendor_id, invoice_number, invoice_date, batch_number,
                expiry_date, quantity, t["amount"], t["cgst"], t["sgst"], t["igst"],
                gst_rate, t["round_off"], t["net_amount"], _now(), bill_id,
            ))
            self.stock_service.receive_stock(
                item_id, vendor_id, quantity, date=invoice_date, bill_id=bill_id,
                txn_type="PURCHASE", remarks=f"Invoice {invoice_number}",
            )

    def delete_bill(self, bill_id):
        """Delete a bill and the stock it added (refused if that stock was already issued)."""
        bill = self.get_bill_by_id(bill_id)
        if not bill:
            return
        with self.db.transaction(), self.stock_service.guard_negative_stock([bill["item_id"]]):
            self._remove_bill_stock(bill)
            self.db.execute("DELETE FROM bills WHERE id = ?", (bill_id,))

    def get_bill_details_view(self):
        return self.db.fetch_all("""
            SELECT
                b.id AS sr_no,
                COALESCE(b.invoice_date, b.entry_date) AS date,
                v.name AS vendor,
                i.name AS item_name,
                b.invoice_number AS invoice_no,
                b.batch_number AS batch_no,
                b.expiry_date,
                b.quantity AS qty,
                b.amount,
                COALESCE(b.gst_rate, 0) AS gst_rate,
                (COALESCE(b.cgst, 0) + COALESCE(b.sgst, 0) + COALESCE(b.igst, 0)) AS tax,
                COALESCE(b.round_off, 0) AS round_off,
                b.net_amount
            FROM bills b
            JOIN vendors v ON b.vendor_id = v.id
            LEFT JOIN items i ON b.item_id = i.id
            ORDER BY COALESCE(b.invoice_date, b.entry_date) DESC, b.id DESC
        """)
