"""
Fill a database with realistic SAMPLE data for previewing the app.

    HOSPITAL_STOCK_DATA_DIR=preview_data python tools/demo_data.py

Creates purchases and weekly issues from April to today, using the default
vendor and item lists. Refuses to run on a database that already has bills,
so it can never mix fake entries into real data.
"""
import os
import random
import sys
from datetime import date, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))


def main():
    from services.db_service import get_db
    from models.migrations import migrate
    from models.seed_data import ensure_admin_user, seed_if_first_run
    from services.bill_service import BillService
    from services.stock_service import StockService, StockError

    db = get_db()
    migrate(db.conn)
    ensure_admin_user(db)
    seed_if_first_run(db)

    if db.scalar("SELECT COUNT(*) FROM bills"):
        print(f"{db.db_path} already has bills - not adding sample data.")
        return

    rng = random.Random(2026)
    bills, stock = BillService(), StockService()
    items = db.fetch_all("SELECT id, name FROM items ORDER BY id")
    vendors = db.fetch_all("SELECT id FROM vendors ORDER BY id")
    rates = [0, 5, 12, 18]

    start = date(date.today().year, 4, 1)
    today = date.today()
    invoice_no = 1000

    with db.transaction():
        # Purchases: a few invoices every ~10 days, 1-4 items each
        d = start
        while d <= today:
            for _ in range(rng.randint(1, 3)):
                vendor = rng.choice(vendors)["id"]
                invoice_no += 1
                gst = rng.choice(rates)
                for item in rng.sample(items, rng.randint(1, 4)):
                    bills.add_bill(
                        item_id=item["id"], vendor_id=vendor,
                        invoice_number=f"INV-{invoice_no}", invoice_date=d.isoformat(),
                        batch_number=f"B{rng.randint(10000, 99999)}",
                        expiry_date=(d + timedelta(days=rng.randint(120, 720))).isoformat(),
                        quantity=rng.choice([5, 10, 20, 25, 50, 100]),
                        rate=rng.choice([45, 80, 120, 250, 480, 900, 1450]),
                        gst_rate=gst,
                    )
            d += timedelta(days=rng.randint(7, 14))

        # Issues: weekly, for items that have stock on that date
        d = start + timedelta(days=3)
        while d <= today:
            for item in rng.sample(items, 12):
                available = stock.get_stock_balance(item["id"], as_of=d.isoformat())
                if available > 0:
                    qty = max(1, min(available, rng.randint(1, max(1, available // 3))))
                    try:
                        stock.issue_stock(item["id"], qty, issue_date=d.isoformat(),
                                          remarks=rng.choice(["Lab", "OPD", "Ward", ""]))
                    except StockError:
                        pass
            d += timedelta(days=7)

    print(f"Sample data added to {db.db_path}: "
          f"{db.scalar('SELECT COUNT(*) FROM bills')} purchase lines, "
          f"{db.scalar('SELECT COUNT(*) FROM stock_register WHERE issued_qty > 0')} issues.")
    db.close()


if __name__ == "__main__":
    main()
