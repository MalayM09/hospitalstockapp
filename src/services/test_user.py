from .user_service import UserService
from .db_service import DatabaseService

u = UserService()
db = DatabaseService()

# Reset admin password to hashed version (only once)
db.execute(
    "UPDATE users SET password_hash = ? WHERE username = 'admin'",
    (u.hash_password("admin"),)
)

print("Login success?", u.login("admin", "admin"))
print("Login fail?", u.login("admin", "wrongpass"))
