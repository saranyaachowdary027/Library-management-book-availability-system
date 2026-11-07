
from pathlib import Path
import sqlite3
from datetime import date, timedelta

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# Resolve the existing project database.
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DB_PATH = PROJECT_ROOT / "library.db"

app = FastAPI(title="Smart Library API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def connect():
    if not DB_PATH.exists():
        raise HTTPException(
            status_code=500,
            detail=f"Existing database not found: {DB_PATH}",
        )
    connection = sqlite3.connect(str(DB_PATH), timeout=10)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def available_copies(connection, book_id):
    book = connection.execute(
        "SELECT total_copies FROM books WHERE id = ?",
        (book_id,),
    ).fetchone()

    if book is None:
        return None

    borrowed = connection.execute(
        """SELECT COUNT(*) FROM loans
           WHERE book_id = ? AND return_date IS NULL""",
        (book_id,),
    ).fetchone()[0]

    return max(0, book["total_copies"] - borrowed)


class BorrowRequest(BaseModel):
    book_id: int
    user_id: str = Field(min_length=1, max_length=100)


class ReturnRequest(BaseModel):
    loan_id: int


@app.get("/")
def root():
    return {
        "message": "Smart Library API is running",
        "docs": "/docs",
    }


@app.get("/api/health")
def health():
    with connect() as db:
        books = db.execute(
            "SELECT COUNT(*) FROM books"
        ).fetchone()[0]
        loans = db.execute(
            "SELECT COUNT(*) FROM loans"
        ).fetchone()[0]

    return {
        "status": "healthy",
        "database": "connected",
        "books": books,
        "loan_records": loans,
    }


@app.get("/api/books")
def list_books(
    search: str = Query(default="", max_length=200),
    category: str = Query(default="", max_length=100),
):
    sql = """
        SELECT id, isbn, title, author, category, total_copies
        FROM books
        WHERE (
            title LIKE ? OR author LIKE ?
            OR isbn LIKE ? OR category LIKE ?
        )
    """
    term = f"%{search}%"
    params = [term, term, term, term]

    if category:
        sql += " AND category = ?"
        params.append(category)

    sql += " ORDER BY title COLLATE NOCASE"

    with connect() as db:
        rows = db.execute(sql, params).fetchall()
        results = []

        for row in rows:
            item = dict(row)
            item["available_copies"] = available_copies(
                db, item["id"]
            )
            results.append(item)

    return results


@app.get("/api/books/{book_id}")
def get_book(book_id: int):
    with connect() as db:
        row = db.execute(
            "SELECT * FROM books WHERE id = ?",
            (book_id,),
        ).fetchone()

        if row is None:
            raise HTTPException(404, "Book not found")

        result = dict(row)
        result["available_copies"] = available_copies(
            db, book_id
        )
        return result


@app.get("/api/dashboard")
def dashboard():
    with connect() as db:
        total_titles = db.execute(
            "SELECT COUNT(*) FROM books"
        ).fetchone()[0]

        total_copies = db.execute(
            "SELECT COALESCE(SUM(total_copies), 0) FROM books"
        ).fetchone()[0]

        active_loans = db.execute(
            "SELECT COUNT(*) FROM loans WHERE return_date IS NULL"
        ).fetchone()[0]

        overdue = db.execute(
            """SELECT COUNT(*) FROM loans
               WHERE return_date IS NULL AND due_date < ?""",
            (date.today().isoformat(),),
        ).fetchone()[0]

        categories = db.execute(
            """SELECT COALESCE(category, 'Uncategorized') AS category,
                      COUNT(*) AS titles
               FROM books GROUP BY category
               ORDER BY titles DESC"""
        ).fetchall()

        popular = db.execute(
            """SELECT b.id, b.title, b.author, COUNT(l.id) AS borrows
               FROM books b
               LEFT JOIN loans l ON l.book_id = b.id
               GROUP BY b.id
               ORDER BY borrows DESC, b.title
               LIMIT 5"""
        ).fetchall()

        available_total = sum(
            available_copies(db, row["id"]) or 0
            for row in db.execute("SELECT id FROM books")
        )

    return {
        "total_titles": total_titles,
        "total_copies": total_copies,
        "available_copies": available_total,
        "active_loans": active_loans,
        "overdue_loans": overdue,
        "categories": [dict(row) for row in categories],
        "popular_books": [dict(row) for row in popular],
    }


@app.get("/api/loans")
def list_loans(active_only: bool = False):
    sql = """
        SELECT l.id AS loan_id, l.book_id, l.user_id,
               l.borrow_date, l.due_date, l.return_date,
               b.title, b.author
        FROM loans l
        JOIN books b ON b.id = l.book_id
    """
    if active_only:
        sql += " WHERE l.return_date IS NULL"
    sql += " ORDER BY l.borrow_date DESC, l.id DESC"

    with connect() as db:
        return [dict(row) for row in db.execute(sql).fetchall()]


@app.post("/api/borrow", status_code=201)
def borrow_book(request: BorrowRequest):
    user_id = request.user_id.strip()
    if not user_id:
        raise HTTPException(400, "User ID is required")

    today = date.today()
    due = today + timedelta(days=14)

    # A transaction prevents simultaneous requests from
    # borrowing the final available copy.
    with connect() as db:
        try:
            db.execute("BEGIN IMMEDIATE")

            copies = available_copies(db, request.book_id)
            if copies is None:
                raise HTTPException(404, "Book not found")
            if copies < 1:
                raise HTTPException(409, "No copies available")

            cursor = db.execute(
                """INSERT INTO loans
                   (book_id, user_id, borrow_date, due_date, return_date)
                   VALUES (?, ?, ?, ?, NULL)""",
                (
                    request.book_id,
                    user_id,
                    today.isoformat(),
                    due.isoformat(),
                ),
            )
            loan_id = cursor.lastrowid
            db.commit()

            return {
                "message": "Book borrowed successfully",
                "loan_id": loan_id,
                "due_date": due.isoformat(),
            }
        except HTTPException:
            db.rollback()
            raise
        except sqlite3.Error as exc:
            db.rollback()
            raise HTTPException(500, "Database operation failed") from exc


@app.post("/api/return")
def return_book(request: ReturnRequest):
    with connect() as db:
        try:
            db.execute("BEGIN IMMEDIATE")
            loan = db.execute(
                "SELECT * FROM loans WHERE id = ?",
                (request.loan_id,),
            ).fetchone()

            if loan is None:
                raise HTTPException(404, "Loan not found")
            if loan["return_date"] is not None:
                raise HTTPException(409, "Book already returned")

            db.execute(
                "UPDATE loans SET return_date = ? WHERE id = ?",
                (date.today().isoformat(), request.loan_id),
            )
            db.commit()

            return {"message": "Book returned successfully"}
        except HTTPException:
            db.rollback()
            raise
        except sqlite3.Error as exc:
            db.rollback()
            raise HTTPException(500, "Database operation failed") from exc
