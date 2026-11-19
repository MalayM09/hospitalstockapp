"""
Shared logic for the simple "master" lists: items and vendors.

Names are trimmed, internal spaces collapsed, and compared case-insensitively,
so "Glucose Kit" and "glucose  kit" can't both exist.
"""
import re

from services.db_service import get_db


class MasterError(ValueError):
    """A refused add/rename/delete, with a message for the user."""


def clean_name(name):
    return re.sub(r"\s+", " ", (name or "")).strip()


class MasterService:
    table = ""        # "items" / "vendors"
    noun = ""         # "item" / "vendor"
    usage_column = "" # column in bills / stock_register that references this table

    def __init__(self):
        self.db = get_db()

    def get_all(self):
        return self.db.fetch_all(f"SELECT id, name FROM {self.table} ORDER BY name COLLATE NOCASE")

    def get(self, row_id):
        return self.db.fetch_one(f"SELECT id, name FROM {self.table} WHERE id = ?", (row_id,))

    def _check_name(self, name, exclude_id=None):
        name = clean_name(name)
        if not name:
            raise MasterError(f"Please enter the {self.noun} name.")
        clash = self.db.fetch_one(
            f"SELECT id, name FROM {self.table} WHERE LOWER(name) = LOWER(?) AND id IS NOT ?",
            (name, exclude_id))
        if clash:
            raise MasterError(f"'{clash['name']}' already exists.")
        return name

    def add(self, name):
        """Add and return the new id."""
        return self.db.execute(f"INSERT INTO {self.table} (name) VALUES (?)", (self._check_name(name),))

    def rename(self, row_id, name):
        self.db.execute(f"UPDATE {self.table} SET name = ? WHERE id = ?",
                        (self._check_name(name, exclude_id=row_id), row_id))

    def usage(self, row_id):
        bills = self.db.scalar(f"SELECT COUNT(*) FROM bills WHERE {self.usage_column} = ?", (row_id,))
        moves = self.db.scalar(f"SELECT COUNT(*) FROM stock_register WHERE {self.usage_column} = ?", (row_id,))
        return bills, moves

    def delete(self, row_id):
        """Delete, unless it is used by any bill or stock entry."""
        bills, moves = self.usage(row_id)
        if bills or moves:
            used = " and ".join(p for p in (f"{bills} bill line(s)" if bills else "",
                                            f"{moves} stock entr{'y' if moves == 1 else 'ies'}" if moves else "") if p)
            raise MasterError(f"This {self.noun} is used in {used}, so it can't be deleted. "
                              f"You can rename it instead.")
        self.db.execute(f"DELETE FROM {self.table} WHERE id = ?", (row_id,))
