import sqlite3
from contextlib import contextmanager


class Inventory:
    def __init__(self, directory):
        self.path = directory / "inventory.sqlite3"
        with self.connect() as db:
            db.execute("CREATE TABLE IF NOT EXISTS items (id INTEGER PRIMARY KEY, name TEXT NOT NULL, quantity INTEGER NOT NULL CHECK(quantity >= 0))")

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path)
        db.row_factory = sqlite3.Row
        try:
            with db:
                yield db
        finally:
            db.close()

    def list(self):
        with self.connect() as db:
            return [dict(row) for row in db.execute("SELECT * FROM items ORDER BY id DESC")]

    def add(self, name, quantity):
        with self.connect() as db:
            db.execute("INSERT INTO items(name,quantity) VALUES (?,?)", (name, quantity))

    def delete(self, identifier):
        with self.connect() as db:
            db.execute("DELETE FROM items WHERE id = ?", (identifier,))
