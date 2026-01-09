from services.db_service import get_db
from services.stock_service import StockService
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP


class BillService:
    def __init__(self):
        self.db = get_db()
        self.stock_service = StockService()

    def add_bill(self, item_id, vendor_id, invoice_number, invoice_date,
                 batch_number, expiry_date, quantity, amount, cgst, sgst, round_off=0.0):
        """
        Add a new bill with automatic net_amount calculation.
        Also automatically updates stock (receives the quantity into inventory).
        """
        # Calculate net_amount using Decimal for precision
        net_amount = Decimal(str(amount)) + Decimal(str(cgst)) + Decimal(str(sgst)) + Decimal(str(round_off))
        net_amount = float(net_amount.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))

        entry_date = datetime.now().strftime("%Y-%m-%d")

        # 1. Insert the bill record
        query = """
        INSERT INTO bills (
            item_id, vendor_id, invoice_number, invoice_date, batch_number,
            expiry_date, quantity, amount, cgst, sgst, round_off, net_amount, entry_date
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        self.db.execute(query, (
            item_id, vendor_id, invoice_number, invoice_date, batch_number,
            expiry_date, quantity, amount, cgst, sgst, round_off, net_amount, entry_date
        ))

        # 2. Automatically update stock (receive the purchased quantity)
        if item_id and quantity and quantity > 0:
            self.stock_service.receive_stock(item_id, vendor_id, quantity)

    def get_recent_bills(self, limit=20):
        """Get recent bills with vendor name."""
        return self.db.fetch_all("""
            SELECT b.id, b.entry_date, v.name AS vendor,
                   b.invoice_number, b.net_amount
            FROM bills b
            JOIN vendors v ON b.vendor_id = v.id
            ORDER BY b.id DESC
            LIMIT ?
        """, (limit,))

    def get_bill_by_id(self, bill_id):
        """Get a specific bill by ID."""
        return self.db.fetch_one("""
            SELECT b.*, v.name AS vendor_name, i.name AS item_name
            FROM bills b
            JOIN vendors v ON b.vendor_id = v.id
            LEFT JOIN items i ON b.item_id = i.id
            WHERE b.id = ?
        """, (bill_id,))

    def update_bill(self, bill_id, item_id, vendor_id, invoice_number, invoice_date,
                    batch_number, expiry_date, quantity, amount, cgst, sgst, round_off=0.0):
        """
        Update an existing bill with stock adjustment.
        Reverses old stock and applies new stock to maintain data integrity.
        """
        # Get original bill data to calculate stock difference
        original_bill = self.get_bill_by_id(bill_id)
        
        net_amount = Decimal(str(amount)) + Decimal(str(cgst)) + Decimal(str(sgst)) + Decimal(str(round_off))
        net_amount = float(net_amount.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))

        query = """
        UPDATE bills SET
            item_id = ?, vendor_id = ?, invoice_number = ?, invoice_date = ?,
            batch_number = ?, expiry_date = ?, quantity = ?, amount = ?, cgst = ?, sgst = ?,
            round_off = ?, net_amount = ?
        WHERE id = ?
        """
        self.db.execute(query, (
            item_id, vendor_id, invoice_number, invoice_date, batch_number,
            expiry_date, quantity, amount, cgst, sgst, round_off, net_amount, bill_id
        ))

        # Adjust stock if item_id or quantity changed
        if original_bill:
            old_item_id = original_bill['item_id']
            old_qty = original_bill['quantity'] or 0
            old_vendor_id = original_bill['vendor_id']
            new_qty = quantity or 0

            # If item changed, reverse old item stock and add to new item
            if old_item_id != item_id:
                # Reverse stock for old item
                if old_item_id and old_qty > 0:
                    self.stock_service.reverse_received_stock(old_item_id, old_vendor_id, old_qty)
                # Add stock for new item
                if item_id and new_qty > 0:
                    self.stock_service.receive_stock(item_id, vendor_id, new_qty)
            else:
                # Same item, just adjust the quantity difference
                qty_diff = new_qty - old_qty
                if qty_diff != 0 and item_id:
                    if qty_diff > 0:
                        # Additional stock received
                        self.stock_service.receive_stock(item_id, vendor_id, qty_diff)
                    else:
                        # Stock needs to be reduced
                        self.stock_service.reverse_received_stock(item_id, vendor_id, abs(qty_diff))

    def delete_bill(self, bill_id):
        """
        Delete a bill by ID and reverse the stock that was added.
        This maintains data integrity by removing the stock that was received
        when the bill was originally created.
        """
        # Get bill data before deletion to reverse stock
        bill = self.get_bill_by_id(bill_id)
        
        if bill:
            item_id = bill['item_id']
            quantity = bill['quantity'] or 0
            vendor_id = bill['vendor_id']
            
            # Reverse the stock that was added when bill was created
            if item_id and quantity > 0:
                self.stock_service.reverse_received_stock(item_id, vendor_id, quantity)
        
        # Now delete the bill
        self.db.execute("DELETE FROM bills WHERE id = ?", (bill_id,))

    def get_bill_details_view(self):
        """Get all bills for table display with vendor names and item names."""
        return self.db.fetch_all("""
            SELECT 
                b.id as sr_no,
                b.entry_date as date,
                v.name as vendor,
                i.name as item_name,
                b.invoice_number as invoice_no,
                b.batch_number as batch_no,
                b.expiry_date,
                b.quantity as qty,
                b.amount,
                (COALESCE(b.cgst, 0) + COALESCE(b.sgst, 0)) as tax,
                COALESCE(b.round_off, 0) as round_off,
                b.net_amount
            FROM bills b
            JOIN vendors v ON b.vendor_id = v.id
            LEFT JOIN items i ON b.item_id = i.id
            ORDER BY b.id ASC
        """)
