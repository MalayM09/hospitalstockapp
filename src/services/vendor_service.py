from services.db_service import DatabaseService
import sqlite3


class VendorService:
    def __init__(self):
        self.db = DatabaseService()

    def get_all_vendors(self):
        """Get all vendors ordered by name."""
        return self.db.fetch_all("SELECT * FROM vendors ORDER BY name ASC")

    def get_vendor_by_id(self, vendor_id):
        """Get a specific vendor by ID."""
        return self.db.fetch_one("SELECT * FROM vendors WHERE id = ?", (vendor_id,))

    def add_vendor(self, name) -> bool:
        """Add a new vendor. Returns False if name already exists."""
        try:
            self.db.execute("INSERT INTO vendors (name) VALUES (?)", (name,))
            return True
        except sqlite3.IntegrityError:
            return False  # Duplicate name

    def update_vendor(self, vendor_id, new_name) -> bool:
        """Update a vendor's name. Returns False if new name already exists."""
        try:
            self.db.execute("UPDATE vendors SET name = ? WHERE id = ?", (new_name, vendor_id))
            return True
        except sqlite3.IntegrityError:
            return False  # Duplicate name

    def check_vendor_dependencies(self, vendor_id):
        """
        Check if vendor has related records in bills or stock_register.
        Returns tuple (has_dependencies: bool, message: str)
        """
        # Check bills
        bill_count = self.db.fetch_one(
            "SELECT COUNT(*) as count FROM bills WHERE vendor_id = ?", (vendor_id,)
        )
        bills = bill_count['count'] if bill_count else 0

        # Check stock register
        stock_count = self.db.fetch_one(
            "SELECT COUNT(*) as count FROM stock_register WHERE vendor_id = ?", (vendor_id,)
        )
        stocks = stock_count['count'] if stock_count else 0

        if bills > 0 or stocks > 0:
            messages = []
            if bills > 0:
                messages.append(f"{bills} bill(s)")
            if stocks > 0:
                messages.append(f"{stocks} stock record(s)")
            return True, f"Cannot delete vendor. It has {' and '.join(messages)} associated with it."
        
        return False, ""

    def delete_vendor(self, vendor_id):
        """
        Delete a vendor by ID.
        Returns tuple (success: bool, error_message: str)
        """
        has_deps, message = self.check_vendor_dependencies(vendor_id)
        if has_deps:
            return False, message
        
        self.db.execute("DELETE FROM vendors WHERE id = ?", (vendor_id,))
        return True, ""

