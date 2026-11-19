from services.master_service import MasterService


class ItemService(MasterService):
    table = "items"
    noun = "item"
    usage_column = "item_id"

    def get_all_with_stats(self):
        """Items with current balance and number of purchase lines."""
        return self.db.fetch_all("""
            SELECT i.id, i.name,
                   COALESCE((SELECT SUM(received_qty) - SUM(issued_qty) FROM stock_register s
                             WHERE s.item_id = i.id), 0) AS balance,
                   (SELECT COUNT(*) FROM bills b WHERE b.item_id = i.id) AS purchases
            FROM items i ORDER BY i.name COLLATE NOCASE
        """)
