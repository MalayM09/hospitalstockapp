import bcrypt

from services.db_service import get_db

MIN_PASSWORD_LENGTH = 4


class UserService:
    def __init__(self):
        self.db = get_db()

    @staticmethod
    def hash_password(plain_password: str) -> str:
        return bcrypt.hashpw(plain_password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        try:
            return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
        except ValueError:  # malformed hash
            return False

    def login(self, username: str, password: str) -> bool:
        """Usernames ignore case and surrounding spaces; passwords are exact."""
        user = self.db.fetch_one("SELECT * FROM users WHERE LOWER(username) = LOWER(?)",
                                 ((username or "").strip(),))
        return bool(user) and self.verify_password(password, user["password_hash"])

    def change_password(self, username: str, current: str, new: str):
        """Raises ValueError with a user-facing message if refused."""
        if not self.login(username, current):
            raise ValueError("The current password is not correct.")
        if len(new) < MIN_PASSWORD_LENGTH:
            raise ValueError(f"The new password must be at least {MIN_PASSWORD_LENGTH} characters.")
        self.db.execute("UPDATE users SET password_hash = ? WHERE LOWER(username) = LOWER(?)",
                        (self.hash_password(new), username.strip()))

    def is_default_password(self, username: str) -> bool:
        return username.strip().lower() == "admin" and self.login("admin", "admin")
