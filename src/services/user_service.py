import bcrypt
import sqlite3
from services.db_service import get_db


class UserService:
    def __init__(self):
        self.db = get_db()

    def hash_password(self, plain_password: str) -> str:
        return bcrypt.hashpw(plain_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))

    def create_user(self, username: str, password: str) -> bool:
        """Create a new user. Returns False if username already exists."""
        try:
            hashed = self.hash_password(password)
            self.db.execute(
                "INSERT INTO users (username, password_hash) VALUES (?, ?)",
                (username, hashed)
            )
            return True
        except sqlite3.IntegrityError:
            return False  # Duplicate username

    def get_user(self, username: str):
        return self.db.fetch_one(
            "SELECT * FROM users WHERE username = ?",
            (username,)
        )

    def login(self, username: str, password: str) -> bool:
        user = self.get_user(username)
        if not user:
            return False

        stored_hash = user["password_hash"]
        return self.verify_password(password, stored_hash)
