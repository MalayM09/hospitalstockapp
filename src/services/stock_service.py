from services.db_service import get_db
from datetime import datetime


class StockService:
    def __init__(self):
        self.db = get_db()

    def get_vendors(self):
        """Get all vendors for dropdown selection."""
        return self.db.fetch_all("SELECT id, name FROM vendors ORDER BY name")

    def get_items(self):
        """Get all items for dropdown selection."""
        return self.db.fetch_all("SELECT id, name FROM items ORDER BY name")

    def receive_stock(self, item_id, vendor_id, qty, remarks=""):
        """Record stock received from vendor."""
        date = datetime.now().strftime("%Y-%m-%d")
        self.db.execute("""
            INSERT INTO stock_register (item_id, vendor_id, received_qty, issued_qty, balance_qty, date)
            VALUES (?, ?, ?, 0, ?, ?)
        """, (item_id, vendor_id, qty, qty, date))

    def reverse_received_stock(self, item_id, vendor_id, qty, remarks=""):
        """
        Reverse stock that was previously received (for bill edits/deletes).
        This creates a negative received entry to offset the original receipt.
        """
        date = datetime.now().strftime("%Y-%m-%d")
        self.db.execute("""
            INSERT INTO stock_register (item_id, vendor_id, received_qty, issued_qty, balance_qty, date)
            VALUES (?, ?, ?, 0, ?, ?)
        """, (item_id, vendor_id, -qty, -qty, date))

    def issue_stock(self, item_id, qty, vendor_id=None, remarks="", issue_date=None):
        """Record stock issued (consumed). Subtracts from balance."""
        date = issue_date if issue_date else datetime.now().strftime("%Y-%m-%d")
        self.db.execute("""
            INSERT INTO stock_register (item_id, vendor_id, received_qty, issued_qty, balance_qty, date)
            VALUES (?, ?, 0, ?, ?, ?)
        """, (item_id, vendor_id, qty, -qty, date))

    def get_stock_issuance_history(self, start_date=None, end_date=None, search_term=None):
        """Get all stock issuance records with optional filtering."""
        query = """
            SELECT 
                s.id as sr_no,
                s.date,
                i.name as item_name,
                s.issued_qty
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
        
        return self.db.fetch_all(query, tuple(params) if params else None)

    def get_stock_balance(self, item_id):
        """Calculate current balance for a specific item: SUM(received) - SUM(issued)."""
        result = self.db.fetch_one("""
            SELECT COALESCE(SUM(received_qty), 0) - COALESCE(SUM(issued_qty), 0) as balance
            FROM stock_register
            WHERE item_id = ?
        """, (item_id,))
        return result["balance"] if result else 0

    def get_all_balances(self):
        """Get balance for all items."""
        return self.db.fetch_all("""
            SELECT i.id, i.name,
                   COALESCE(SUM(s.received_qty), 0) as total_received,
                   COALESCE(SUM(s.issued_qty), 0) as total_issued,
                   COALESCE(SUM(s.received_qty), 0) - COALESCE(SUM(s.issued_qty), 0) as balance
            FROM items i
            LEFT JOIN stock_register s ON i.id = s.item_id
            GROUP BY i.id, i.name
            ORDER BY i.name
        """)

    def get_stock_history(self, item_id=None, limit=50):
        """Get stock transaction history, optionally filtered by item."""
        if item_id:
            return self.db.fetch_all("""
                SELECT s.id, s.date, i.name as item_name, v.name as vendor_name,
                       s.received_qty, s.issued_qty
                FROM stock_register s
                JOIN items i ON s.item_id = i.id
                LEFT JOIN vendors v ON s.vendor_id = v.id
                WHERE s.item_id = ?
                ORDER BY s.id DESC
                LIMIT ?
            """, (item_id, limit))
        else:
            return self.db.fetch_all("""
                SELECT s.id, s.date, i.name as item_name, v.name as vendor_name,
                       s.received_qty, s.issued_qty
                FROM stock_register s
                JOIN items i ON s.item_id = i.id
                LEFT JOIN vendors v ON s.vendor_id = v.id
                ORDER BY s.id DESC
                LIMIT ?
            """, (limit,))

    def get_stock_register_view(self):
        """Get stock summary per item with total received, issued, and balance for table display."""
        return self.db.fetch_all("""
            SELECT 
                i.id as sr_no,
                i.name as lab_item,
                COALESCE(SUM(s.received_qty), 0) as received_qty,
                COALESCE(SUM(s.issued_qty), 0) as issued_qty,
                COALESCE(SUM(s.received_qty), 0) - COALESCE(SUM(s.issued_qty), 0) as balance_qty
            FROM items i
            LEFT JOIN stock_register s ON i.id = s.item_id
            GROUP BY i.id, i.name
            ORDER BY i.id ASC
        """)
