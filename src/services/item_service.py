from services.db_service import get_db
import sqlite3


class ItemService:
    def __init__(self):
        self.db = get_db()

    def get_all_items(self):
        """Get all items ordered by name."""
        return self.db.fetch_all("SELECT * FROM items ORDER BY name ASC")

    def get_item_by_id(self, item_id):
        """Get a specific item by ID."""
        return self.db.fetch_one("SELECT * FROM items WHERE id = ?", (item_id,))

    def add_item(self, name) -> bool:
        """Add a new item. Returns False if name already exists."""
        try:
            self.db.execute("INSERT INTO items (name) VALUES (?)", (name,))
            return True
        except sqlite3.IntegrityError:
            return False  # Duplicate name

    def update_item(self, item_id, new_name) -> bool:
        """Update an item's name. Returns False if new name already exists."""
        try:
            self.db.execute("UPDATE items SET name = ? WHERE id = ?", (new_name, item_id))
            return True
        except sqlite3.IntegrityError:
            return False  # Duplicate name

    def check_item_dependencies(self, item_id):
        """
        Check if item has related records in bills or stock_register.
        Returns tuple (has_dependencies: bool, message: str)
        """
        # Check bills
        bill_count = self.db.fetch_one(
            "SELECT COUNT(*) as count FROM bills WHERE item_id = ?", (item_id,)
        )
        bills = bill_count['count'] if bill_count else 0

        # Check stock register
        stock_count = self.db.fetch_one(
            "SELECT COUNT(*) as count FROM stock_register WHERE item_id = ?", (item_id,)
        )
        stocks = stock_count['count'] if stock_count else 0

        if bills > 0 or stocks > 0:
            messages = []
            if bills > 0:
                messages.append(f"{bills} bill(s)")
            if stocks > 0:
                messages.append(f"{stocks} stock record(s)")
            return True, f"Cannot delete item. It has {' and '.join(messages)} associated with it."
        
        return False, ""

    def delete_item(self, item_id):
        """
        Delete an item by ID.
        Returns tuple (success: bool, error_message: str)
        """
        has_deps, message = self.check_item_dependencies(item_id)
        if has_deps:
            return False, message
        
        self.db.execute("DELETE FROM items WHERE id = ?", (item_id,))
        return True, ""

