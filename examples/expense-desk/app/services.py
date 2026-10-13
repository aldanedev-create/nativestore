import sqlite3
from contextlib import contextmanager
from pathlib import Path


class ExpenseService:
    def __init__(self, database: Path):
        self.database = database
        database.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as connection:
            connection.execute(
                "CREATE TABLE IF NOT EXISTS expenses (id INTEGER PRIMARY KEY, "
                "description TEXT NOT NULL, amount_cents INTEGER NOT NULL CHECK(amount_cents > 0), "
                "category TEXT NOT NULL, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)"
            )

    @contextmanager
    def connect(self):
        connection = sqlite3.connect(self.database)
        connection.row_factory = sqlite3.Row
        try:
            with connection:
                yield connection
        finally:
            connection.close()

    def add(self, description: str, amount_cents: int, category: str) -> int:
        description = description.strip()
        category = category.strip()
        if not 1 <= len(description) <= 200 or not 1 <= len(category) <= 50:
            raise ValueError("Description and category are required")
        if type(amount_cents) is not int or not 0 < amount_cents <= 1_000_000_000:
            raise ValueError("Amount must be a positive integer number of cents")
        with self.connect() as connection:
            cursor = connection.execute(
                "INSERT INTO expenses(description, amount_cents, category) VALUES (?, ?, ?)",
                (description, amount_cents, category),
            )
            return int(cursor.lastrowid)

    def list(self) -> list[dict[str, str | int]]:
        with self.connect() as connection:
            return [
                dict(row) for row in connection.execute("SELECT * FROM expenses ORDER BY id DESC")
            ]

    def delete(self, expense_id: int) -> bool:
        if type(expense_id) is not int or expense_id <= 0:
            raise ValueError("Invalid expense ID")
        with self.connect() as connection:
            return (
                connection.execute("DELETE FROM expenses WHERE id = ?", (expense_id,)).rowcount == 1
            )
