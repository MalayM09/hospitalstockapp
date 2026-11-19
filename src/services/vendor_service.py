from services.master_service import MasterService


class VendorService(MasterService):
    table = "vendors"
    noun = "vendor"
    usage_column = "vendor_id"

    def get_all_with_stats(self):
        """Vendors with number of invoices and total purchased (Rs)."""
        return self.db.fetch_all("""
            SELECT v.id, v.name,
                   COUNT(DISTINCT b.invoice_number) AS invoices,
                   COALESCE(SUM(b.net_amount), 0) AS total,
                   MAX(COALESCE(b.invoice_date, b.entry_date)) AS last_purchase
            FROM vendors v LEFT JOIN bills b ON b.vendor_id = v.id
            GROUP BY v.id ORDER BY v.name COLLATE NOCASE
        """)
