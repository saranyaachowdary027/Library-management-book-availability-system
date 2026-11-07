
import sys
from pathlib import Path

import streamlit as st
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from database.db import get_connection, initialize_database

st.set_page_config(
    page_title="Live Library Inventory",
    page_icon="📚",
    layout="wide",
)

initialize_database()

st.title("📚 Live Library Inventory")
st.caption("Current book availability from your library database.")

with get_connection() as conn:
    books = pd.read_sql_query(
        """
        SELECT
            b.id AS book_id,
            b.title,
            b.author,
            b.category,
            b.total_copies,
            b.total_copies - (
                SELECT COUNT(*)
                FROM loans l
                WHERE l.book_id = b.id
                  AND l.return_date IS NULL
            ) AS available_copies
        FROM books b
        ORDER BY b.title
        """,
        conn,
    )

if books.empty:
    st.warning("No books found in the catalogue.")
    st.stop()

search = st.text_input("Search by title, author, or category")

if search.strip():
    mask = (
        books["title"].fillna("").str.contains(
            search, case=False, regex=False
        )
        | books["author"].fillna("").str.contains(
            search, case=False, regex=False
        )
        | books["category"].fillna("").str.contains(
            search, case=False, regex=False
        )
    )
    books = books[mask]

total_titles = len(books)
total_copies = int(books["total_copies"].sum())
available_copies = int(books["available_copies"].clip(lower=0).sum())
borrowed_copies = total_copies - available_copies

col1, col2, col3, col4 = st.columns(4)
col1.metric("Book titles", total_titles)
col2.metric("Total copies", total_copies)
col3.metric("Available copies", available_copies)
col4.metric("Borrowed copies", borrowed_copies)

st.subheader("Current availability")

display = books.rename(columns={
    "book_id": "Book ID",
    "title": "Title",
    "author": "Author",
    "category": "Category",
    "total_copies": "Total Copies",
    "available_copies": "Available Copies",
})

st.dataframe(
    display,
    use_container_width=True,
    hide_index=True,
)

st.caption(
    "Availability is calculated from the live SQLite catalogue "
    "and active loan records."
)

if st.button("Refresh inventory"):
    st.rerun()
