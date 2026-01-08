from .user_service import UserService
from .db_service import DatabaseService


db = DatabaseService()

print("Users:")
rows = db.fetch_all("SELECT * FROM users")
for r in rows:
    print(dict(r))

print("\nVendors count:", len(db.fetch_all("SELECT * FROM vendors")))
print("Items count:", len(db.fetch_all("SELECT * FROM items")))
