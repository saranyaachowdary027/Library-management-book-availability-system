
import sys
from pathlib import Path
from datetime import date, timedelta
import sqlite3

import pandas as pd
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from database.db import get_connection, initialize_database

st.set_page_config(
    page_title="Borrow & Return",
    page_icon="📚",
    layout="wide",
)

initialize_database()

st.title("📚 Borrow & Return Books")
st.caption("Borrow books, record returns, and review loan history.")

with get_connection() as conn:
    books = conn.execute("""
        SELECT id, title, author, total_copies
        FROM books
        ORDER BY title
    """).fetchall()

if not books:
    st.warning("No books found. Add books to the catalogue first.")
    st.stop()

book_options = {
    f"{book['title']} — {book['author']} (ID {book['id']})": book["id"]
    for book in books
}

tab_borrow, tab_return, tab_history = st.tabs([
    "Borrow a book",
    "Return a book",
    "Loan history",
])

with tab_borrow:
    st.subheader("New borrowing record")

    with st.form("borrow_form"):
        selected_book = st.selectbox("Book", list(book_options.keys()))
        user_id = st.text_input("Student / User ID").strip()
        borrow_date = st.date_input("Borrow date", value=date.today())
        due_date = st.date_input(
            "Due date",
            value=date.today() + timedelta(days=14),
        )
        submitted = st.form_submit_button("Borrow book")

    if submitted:
        book_id = book_options[selected_book]

        if not user_id:
            st.error("Enter a student or user ID.")
        elif due_date < borrow_date:
            st.error("Due date cannot be before the borrow date.")
        else:
            try:
                error_message = None

                with get_connection() as conn:
                    conn.execute("BEGIN IMMEDIATE")

                    book = conn.execute(
                        "SELECT total_copies FROM books WHERE id = ?",
                        (book_id,),
                    ).fetchone()

                    if book is None:
                        error_message = "The selected book no longer exists."
                    else:
                        active = conn.execute("""
                            SELECT COUNT(*)
                            FROM loans
                            WHERE book_id = ?
                              AND return_date IS NULL
                        """, (book_id,)).fetchone()[0]

                        if int(book["total_copies"]) - active <= 0:
                            error_message = "No copies are currently available."
                        else:
                            conn.execute("""
                                INSERT INTO loans
                                    (book_id, user_id, borrow_date, due_date)
                                VALUES (?, ?, ?, ?)
                            """, (
                                book_id,
                                user_id,
                                borrow_date.isoformat(),
                                due_date.isoformat(),
                            ))

                # The connection block has exited; the transaction is committed.
                if error_message:
                    st.error(error_message)
                else:
                    st.success(
                        f"Book borrowed successfully for {user_id}. "
                        "Open Loan history to verify the record."
                    )

            except (sqlite3.Error, OSError) as error:
                st.error(f"Could not save the borrowing record: {error}")

with tab_return:
    st.subheader("Return a borrowed book")

    with get_connection() as conn:
        active_loans = conn.execute("""
            SELECT
                l.id, b.title, l.user_id, l.borrow_date, l.due_date
            FROM loans l
            JOIN books b ON b.id = l.book_id
            WHERE l.return_date IS NULL
            ORDER BY l.due_date
        """).fetchall()

    if not active_loans:
        st.info("There are no active loans to return.")
    else:
        loan_options = {
            f"Loan {loan['id']} — {loan['title']} | "
            f"User {loan['user_id']} | Due {loan['due_date']}":
                loan["id"]
            for loan in active_loans
        }

        with st.form("return_form"):
            selected_loan = st.selectbox(
                "Select active loan", list(loan_options.keys())
            )
            returned_on = st.date_input(
                "Return date", value=date.today()
            )
            return_submitted = st.form_submit_button("Confirm return")

        if return_submitted:
            loan_id = loan_options[selected_loan]

            try:
                error_message = None

                with get_connection() as conn:
                    conn.execute("BEGIN IMMEDIATE")

                    loan = conn.execute("""
                        SELECT borrow_date, return_date
                        FROM loans
                        WHERE id = ?
                    """, (loan_id,)).fetchone()

                    if loan is None:
                        error_message = "Loan record not found."
                    elif returned_on.isoformat() < loan["borrow_date"]:
                        error_message = (
                            "Return date cannot be before borrow date."
                        )
                    elif loan["return_date"] is not None:
                        error_message = "This book has already been returned."
                    else:
                        conn.execute("""
                            UPDATE loans
                            SET return_date = ?
                            WHERE id = ? AND return_date IS NULL
                        """, (returned_on.isoformat(), loan_id))

                if error_message:
                    st.error(error_message)
                else:
                    st.success("Book returned successfully.")

            except (sqlite3.Error, OSError) as error:
                st.error(f"Could not save the return: {error}")

with tab_history:
    st.subheader("All borrowing records")

    with get_connection() as conn:
        records = pd.read_sql_query("""
            SELECT
                l.id AS loan_id,
                b.title,
                l.user_id,
                l.borrow_date,
                l.due_date,
                l.return_date,
                CASE
                    WHEN l.return_date IS NOT NULL THEN 'Returned'
                    WHEN l.due_date < DATE('now') THEN 'Overdue'
                    ELSE 'Borrowed'
                END AS status
            FROM loans l
            JOIN books b ON b.id = l.book_id
            ORDER BY l.id DESC
        """, conn)

    if records.empty:
        st.info("No borrowing records yet.")
    else:
        st.dataframe(
            records,
            use_container_width=True,
            hide_index=True,
        )
