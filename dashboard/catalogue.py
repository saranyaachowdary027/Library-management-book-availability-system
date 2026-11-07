
import sys
from pathlib import Path

import streamlit as st
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from database.db import get_connection, initialize_database

st.set_page_config(
    page_title="Book Catalogue",
    page_icon="📚",
    layout="wide",
)

initialize_database()

st.title("📚 Library Book Catalogue")
st.caption("Search books and check current copy availability.")

search = st.text_input("Search by title, author, ISBN, or category")

with get_connection() as connection:
    books = pd.read_sql_query("""
        SELECT
            b.id,
            b.isbn,
            b.title,
            b.author,
            b.category,
            b.total_copies,
            MAX(
                0,
                b.total_copies - (
                    SELECT COUNT(*)
                    FROM loans l
                    WHERE l.book_id = b.id
                      AND l.return_date IS NULL
                )
            ) AS available_copies
        FROM books b
        GROUP BY b.id
        ORDER BY b.title
    """, connection)

if search:
    columns = ["title", "author", "isbn", "category"]
    mask = books[columns].fillna("").astype(str).apply(
        lambda column: column.str.contains(
            search, case=False, regex=False
        )
    ).any(axis=1)
    books = books[mask]

if books.empty:
    st.info("No matching books found.")
else:
    st.metric("Matching titles", len(books))
    st.dataframe(
        books.rename(columns={
            "id": "Book ID",
            "isbn": "ISBN",
            "title": "Title",
            "author": "Author",
            "category": "Category",
            "total_copies": "Total Copies",
            "available_copies": "Available Copies",
        }),
        use_container_width=True,
        hide_index=True,
    )
