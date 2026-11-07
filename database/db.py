
import sqlite3
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_ROOT / "library.db"


def get_connection():
    connection = sqlite3.connect(str(DB_PATH), timeout=10)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def initialize_database():
    with get_connection() as connection:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS books (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                isbn TEXT UNIQUE,
                title TEXT NOT NULL,
                author TEXT NOT NULL,
                category TEXT,
                total_copies INTEGER NOT NULL DEFAULT 1
                    CHECK (total_copies >= 0)
            )
        """)

        connection.execute("""
            CREATE TABLE IF NOT EXISTS loans (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                book_id INTEGER NOT NULL,
                user_id TEXT NOT NULL,
                borrow_date TEXT NOT NULL,
                due_date TEXT NOT NULL,
                return_date TEXT DEFAULT NULL,
                FOREIGN KEY (book_id) REFERENCES books(id)
            )
        """)


def get_available_copies(book_id):
    with get_connection() as connection:
        book = connection.execute(
            "SELECT total_copies FROM books WHERE id = ?",
            (book_id,),
        ).fetchone()

        if book is None:
            return None

        borrowed = connection.execute("""
            SELECT COUNT(*)
            FROM loans
            WHERE book_id = ? AND return_date IS NULL
        """, (book_id,)).fetchone()[0]

        return max(0, book["total_copies"] - borrowed)


if __name__ == "__main__":
    initialize_database()
    print(f"Database initialized: {DB_PATH}")
