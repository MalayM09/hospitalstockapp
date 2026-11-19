"""
Purchase bills.

An invoice from a vendor may contain several items. Each item is stored as one
row in `bills` (sharing vendor, invoice number and date), and each row creates
one linked PURCHASE row in the stock register dated on the invoice date.

The invoice total is rounded to the rupee once; that round-off is stored on the
invoice's last line, so the lines always add up to the invoice's net amount.

Saving, editing and deleting always happen in one transaction together with the
stock rows, and are refused if they would make stock negative on any date.
"""
from datetime import date as _date, datetime
from decimal import Decimal

from services.db_service import get_db
from services.gst import line_totals, round_off, to_decimal
from services.stock_service import StockService, StockError


def _now():
    return datetime.now().isoformat(timespec="seconds")


def _validate_line(line):
    if not line.get("item_id"):
        raise StockError("Every line needs an item.")
    qty = line.get("quantity")
    if not isinstance(qty, int) or qty <= 0:
        raise StockError("Quantity must be a whole number greater than zero.")
    if to_decimal(line.get("rate")) < 0:
        raise StockError("Rate cannot be negative.")


class BillService:
    def __init__(self):
        self.db = get_db()
        self.stock_service = StockService()

    # ---- create ------------------------------------------------------------------

    def add_invoice(self, vendor_id, invoice_number, invoice_date, lines, interstate=False):
        """
        Save a whole invoice. `lines`: list of dicts with item_id, quantity, rate,
        gst_rate and optional batch_number, expiry_date (YYYY-MM-DD or None).
        Returns the list of new bill ids.
        """
        invoice_number = (invoice_number or "").strip()
        if not vendor_id:
            raise StockError("Please select a vendor.")
        if not invoice_number:
            raise StockError("Please enter the invoice number.")
        if not lines:
            raise StockError("Add at least one item to the invoice.")
        for ln in lines:
            _validate_line(ln)

        now, today = _now(), _date.today().isoformat()
        ids = []
        with self.db.transaction():
            for ln in lines:
                t = line_totals(ln["quantity"], ln["rate"], ln["gst_rate"], interstate)
                bill_id = self.db.execute("""
                    INSERT INTO bills (
                        item_id, vendor_id, invoice_number, invoice_date, batch_number,
                        expiry_date, quantity, amount, cgst, sgst, igst, gst_rate,
                        round_off, net_amount, entry_date, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?, ?, ?, ?)
                """, (
                    ln["item_id"], vendor_id, invoice_number, invoice_date,
                    (ln.get("batch_number") or "").strip(), ln.get("expiry_date") or None,
                    ln["quantity"], float(t["amount"]), float(t["cgst"]), float(t["sgst"]),
                    float(t["igst"]), ln["gst_rate"], float(t["total"]), today, now, now,
                ))
                self.stock_service.receive_stock(
                    ln["item_id"], vendor_id, ln["quantity"], date=invoice_date,
                    bill_id=bill_id, txn_type="PURCHASE", remarks=f"Invoice {invoice_number}",
                )
                ids.append(bill_id)
            self._rebalance_invoice(vendor_id, invoice_number)
        return ids

    def add_bill(self, item_id, vendor_id, invoice_number, invoice_date, batch_number,
                 expiry_date, quantity, rate, gst_rate, interstate=False):
        """Save a single-item invoice. Returns the new bill id."""
        return self.add_invoice(vendor_id, invoice_number, invoice_date, [{
            "item_id": item_id, "quantity": quantity, "rate": rate, "gst_rate": gst_rate,
            "batch_number": batch_number, "expiry_date": expiry_date,
        }], interstate)[0]

    def invoice_exists(self, vendor_id, invoice_number):
        """True if this vendor already has a bill with this invoice number."""
        return bool(self.db.scalar(
            "SELECT 1 FROM bills WHERE vendor_id = ? AND TRIM(LOWER(invoice_number)) = TRIM(LOWER(?)) LIMIT 1",
            (vendor_id, invoice_number)))

    def _rebalance_invoice(self, vendor_id, invoice_number):
        """Put the invoice's rupee round-off on its last line; other lines get none."""
        rows = self.db.fetch_all("""
            SELECT id, amount, cgst, sgst, COALESCE(igst, 0) AS igst FROM bills
            WHERE vendor_id = ? AND invoice_number = ? ORDER BY id
        """, (vendor_id, invoice_number))
        if not rows:
            return
        line_total = {r["id"]: sum(to_decimal(r[k]) for k in ("amount", "cgst", "sgst", "igst")) for r in rows}
        ro = round_off(sum(line_total.values(), Decimal(0)))
        last = rows[-1]["id"]
        for r in rows:
            extra = ro if r["id"] == last else Decimal(0)
            self.db.execute("UPDATE bills SET round_off = ?, net_amount = ? WHERE id = ?",
                            (float(extra), float(line_total[r["id"]] + extra), r["id"]))

    # ---- read --------------------------------------------------------------------

    def get_bill_by_id(self, bill_id):
        return self.db.fetch_one("""
            SELECT b.*, v.name AS vendor_name, i.name AS item_name
            FROM bills b
            JOIN vendors v ON b.vendor_id = v.id
            LEFT JOIN items i ON b.item_id = i.id
            WHERE b.id = ?
        """, (bill_id,))

    def list_bills(self, start_date=None, end_date=None):
        """Bill lines for the Bills screen, newest invoice first."""
        query = """
            SELECT b.id, COALESCE(b.invoice_date, b.entry_date) AS date, b.invoice_number,
                   v.name AS vendor, COALESCE(i.name, '-') AS item, COALESCE(b.batch_number, '') AS batch,
                   COALESCE(b.expiry_date, '') AS expiry, b.quantity,
                   CASE WHEN b.quantity > 0 THEN ROUND(b.amount / b.quantity, 2) ELSE b.amount END AS rate,
                   b.amount, COALESCE(b.gst_rate, 0) AS gst_rate,
                   COALESCE(b.cgst, 0) + COALESCE(b.sgst, 0) + COALESCE(b.igst, 0) AS tax,
                   COALESCE(b.round_off, 0) AS round_off, b.net_amount
            FROM bills b
            JOIN vendors v ON b.vendor_id = v.id
            LEFT JOIN items i ON b.item_id = i.id
            WHERE 1 = 1
        """
        params = []
        if start_date:
            query += " AND COALESCE(b.invoice_date, b.entry_date) >= ?"
            params.append(start_date)
        if end_date:
            query += " AND COALESCE(b.invoice_date, b.entry_date) <= ?"
            params.append(end_date)
        query += " ORDER BY date DESC, b.invoice_number, b.id"
        return self.db.fetch_all(query, params)

    # ---- edit / delete -------------------------------------------------------------

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
        """Edit one bill line; its stock row, taxes and the invoice round-off follow."""
        old = self.get_bill_by_id(bill_id)
        if not old:
            raise StockError("That bill no longer exists.")
        invoice_number = (invoice_number or "").strip()
        if not vendor_id:
            raise StockError("Please select a vendor.")
        if not invoice_number:
            raise StockError("Please enter the invoice number.")
        _validate_line({"item_id": item_id, "quantity": quantity, "rate": rate})
        t = line_totals(quantity, rate, gst_rate, interstate)

        with self.db.transaction(), \
                self.stock_service.guard_negative_stock([old["item_id"], item_id]):
            self._remove_bill_stock(old)
            self.db.execute("""
                UPDATE bills SET
                    item_id = ?, vendor_id = ?, invoice_number = ?, invoice_date = ?,
                    batch_number = ?, expiry_date = ?, quantity = ?, amount = ?,
                    cgst = ?, sgst = ?, igst = ?, gst_rate = ?, round_off = 0,
                    net_amount = ?, updated_at = ?
                WHERE id = ?
            """, (
                item_id, vendor_id, invoice_number, invoice_date, (batch_number or "").strip(),
                expiry_date or None, quantity, float(t["amount"]), float(t["cgst"]), float(t["sgst"]),
                float(t["igst"]), gst_rate, float(t["total"]), _now(), bill_id,
            ))
            self.stock_service.receive_stock(
                item_id, vendor_id, quantity, date=invoice_date, bill_id=bill_id,
                txn_type="PURCHASE", remarks=f"Invoice {invoice_number}",
            )
            self._rebalance_invoice(vendor_id, invoice_number)
            if (old["vendor_id"], old["invoice_number"]) != (vendor_id, invoice_number):
                self._rebalance_invoice(old["vendor_id"], old["invoice_number"])

    def delete_bill(self, bill_id):
        """Delete a bill line and the stock it added (refused if that stock was already issued)."""
        bill = self.get_bill_by_id(bill_id)
        if not bill:
            return
        with self.db.transaction(), self.stock_service.guard_negative_stock([bill["item_id"]]):
            self._remove_bill_stock(bill)
            self.db.execute("DELETE FROM bills WHERE id = ?", (bill_id,))
            self._rebalance_invoice(bill["vendor_id"], bill["invoice_number"])
