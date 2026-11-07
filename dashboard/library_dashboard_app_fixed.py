
import sys
import sqlite3
from pathlib import Path
from datetime import date, timedelta

import pandas as pd
import streamlit as st

# --------------------------------------------------
# Configuration
# --------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "library.db"
DATA_FILE = BASE_DIR / "data" / "processed" / "library_datasets_cleaned.csv"

if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

st.set_page_config(
    page_title="Library Management",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --------------------------------------------------
# Styling
# --------------------------------------------------
st.markdown("""
<style>
.stApp { background: #f4f6fb; color: #172033; }
.block-container { padding-top: 1.4rem; max-width: 1500px; }
[data-testid="stSidebar"] { background: #111a31; }
[data-testid="stSidebar"] * { color: #f5f7ff; }
[data-testid="stMetric"] {
    background: white; border: 1px solid #e4e8f2;
    border-radius: 14px; padding: 18px;
    box-shadow: 0 3px 12px rgba(25,35,70,.05);
}
[data-testid="stMetricLabel"] { color: #64748b; }
[data-testid="stMetricValue"] { color: #172033; font-weight: 750; }
.stButton > button, .stFormSubmitButton > button {
    background: #7048e8; color: white; border: 0;
    border-radius: 9px; min-height: 40px; font-weight: 600;
}
.stButton > button:hover, .stFormSubmitButton > button:hover {
    background: #5b35cc; color: white; border: 0;
}
h1, h2, h3 { color: #172033; }
</style>
""", unsafe_allow_html=True)

# --------------------------------------------------
# Database helpers
# --------------------------------------------------
def connect():
    if not DB_PATH.exists():
        raise FileNotFoundError(f"Database not found: {DB_PATH}")
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def load_books():
    with connect() as conn:
        return pd.read_sql_query(
            """
            SELECT b.id AS book_id, b.title, b.author, b.category,
                   b.total_copies,
                   b.total_copies - (
                       SELECT COUNT(*) FROM loans l
                       WHERE l.book_id = b.id AND l.return_date IS NULL
                   ) AS available_copies
            FROM books b
            ORDER BY b.title
            """,
            conn,
        )


def load_loans():
    with connect() as conn:
        return pd.read_sql_query(
            """
            SELECT l.id AS loan_id, b.title, b.author,
                   l.user_id, l.borrow_date, l.due_date,
                   l.return_date
            FROM loans l
            LEFT JOIN books b ON b.id = l.book_id
            ORDER BY l.id DESC
            """,
            conn,
        )


def check_schema():
    with connect() as conn:
        tables = {
            row["name"]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }
        if not {"books", "loans"}.issubset(tables):
            st.error(
                "Your database must contain 'books' and 'loans' tables. "
                "This app will not recreate or overwrite your database."
            )
            st.stop()

        book_cols = {
            row["name"] for row in conn.execute("PRAGMA table_info(books)")
        }
        loan_cols = {
            row["name"] for row in conn.execute("PRAGMA table_info(loans)")
        }

        required_books = {"id", "title", "author", "category", "total_copies"}
        required_loans = {
            "id", "book_id", "borrow_date", "return_date"
        }

        if not required_books.issubset(book_cols):
            st.error(f"Books table columns found: {sorted(book_cols)}")
            st.stop()
        if not required_loans.issubset(loan_cols):
            st.error(f"Loans table columns found: {sorted(loan_cols)}")
            st.stop()


# --------------------------------------------------
# App navigation
# --------------------------------------------------
with st.sidebar:
    st.markdown("# 📚 LIBRARY")
    st.caption("Management workspace")
    st.divider()
    page = st.radio(
        "NAVIGATION",
        [
            "Overview",
            "Live Inventory",
            "Catalogue",
            "Borrow & Return",
            "Analytics",
        ],
        label_visibility="visible",
    )
    st.divider()
    st.caption("Library Management System")


st.title("📚 Library Management")
st.caption("Monitor inventory, manage circulation, and explore library activity.")

# Keep action confirmations visible after st.rerun().
if st.session_state.get("success_message"):
    st.success(st.session_state["success_message"])
    if st.button("Dismiss message", key="dismiss_success_message"):
        del st.session_state["success_message"]
        st.rerun()


try:
    check_schema()
    books = load_books()
    loans = load_loans()
except (sqlite3.Error, FileNotFoundError) as exc:
    st.error(f"Unable to read the existing library database: {exc}")
    st.info(f"Expected database location: {DB_PATH}")
    st.stop()

if not books.empty:
    books["available_copies"] = books["available_copies"].clip(lower=0)

active_loans = loans[loans["return_date"].isna()] if not loans.empty else loans
total_titles = len(books)
total_copies = int(books["total_copies"].fillna(0).sum()) if not books.empty else 0
available_copies = int(books["available_copies"].fillna(0).sum()) if not books.empty else 0
borrowed_copies = len(active_loans)
overdue_count = 0

if not active_loans.empty and "due_date" in active_loans.columns:
    due_dates = pd.to_datetime(active_loans["due_date"], errors="coerce")
    overdue_count = int((due_dates.dt.date < date.today()).sum())

# --------------------------------------------------
# Overview
# --------------------------------------------------
if page == "Overview":
    st.subheader("Overview")

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Book titles", f"{total_titles:,}")
    k2.metric("Total copies", f"{total_copies:,}")
    k3.metric("Available copies", f"{available_copies:,}")
    k4.metric("Currently borrowed", f"{borrowed_copies:,}")

    st.write("")
    left, right = st.columns([1.5, 1])

    with left:
        st.subheader("📈 Collection availability")
        if not books.empty:
            chart = books[["title", "available_copies", "total_copies"]].set_index("title")
            st.bar_chart(chart)
        else:
            st.info("No books are in the catalogue yet.")

    with right:
        st.subheader("⏰ Circulation status")
        st.metric("Overdue loans", overdue_count)
        st.metric("Books with no copies available", int((books["available_copies"] == 0).sum()) if not books.empty else 0)
        st.metric("Active loans", borrowed_copies)

    st.subheader("📋 Current inventory")
    if not books.empty:
        st.dataframe(books, use_container_width=True, hide_index=True)

    st.subheader("⚡ Quick actions")
    q1, q2, q3 = st.columns(3)
    with q1:
        if st.button("📚 Browse catalogue", use_container_width=True):
            st.session_state["requested_page"] = "Catalogue"
            st.rerun()
    with q2:
        if st.button("➕ Borrow a book", use_container_width=True):
            st.session_state["requested_page"] = "Borrow & Return"
            st.rerun()
    with q3:
        if st.button("📦 View inventory", use_container_width=True):
            st.session_state["requested_page"] = "Live Inventory"
            st.rerun()

# --------------------------------------------------
# Live Inventory
# --------------------------------------------------
elif page == "Live Inventory":
    st.subheader("📦 Live Inventory")
    search = st.text_input("Search by title, author, or category")

    result = books.copy()
    if search.strip():
        mask = result[["title", "author", "category"]].fillna("").astype(str).apply(
            lambda col: col.str.contains(search.strip(), case=False, regex=False)
        ).any(axis=1)
        result = result[mask]

    a, b, c = st.columns(3)
    a.metric("Titles", len(result))
    b.metric("Available copies", int(result["available_copies"].sum()) if not result.empty else 0)
    c.metric("Unavailable copies", int((result["total_copies"] - result["available_copies"]).clip(lower=0).sum()) if not result.empty else 0)

    st.dataframe(result, use_container_width=True, hide_index=True)

# --------------------------------------------------
# Catalogue
# --------------------------------------------------
elif page == "Catalogue":
    st.subheader("📖 Book Catalogue")
    search = st.text_input("Search catalogue", placeholder="Title, author, or category")

    result = books.copy()
    if search.strip():
        mask = result[["title", "author", "category"]].fillna("").astype(str).apply(
            lambda col: col.str.contains(search.strip(), case=False, regex=False)
        ).any(axis=1)
        result = result[mask]

    st.dataframe(result, use_container_width=True, hide_index=True)

# --------------------------------------------------
# Borrow & Return
# --------------------------------------------------
elif page == "Borrow & Return":
    st.subheader("🔄 Borrow & Return")
    st.caption("Borrowing and return records are stored in your existing SQLite database.")

    available_books = books[books["available_copies"] > 0].copy()

    borrow_tab, return_tab, history_tab = st.tabs(
        ["➕ Borrow a book", "↩️ Return a book", "📋 Loan history"]
    )

    with borrow_tab:
        if available_books.empty:
            st.warning("No books are currently available to borrow.")
        else:
            options = {
                f'{row.title} — {row.author} ({int(row.available_copies)} available)': int(row.book_id)
                for row in available_books.itertuples()
            }
            with st.form("borrow_form", clear_on_submit=True):
                selected_label = st.selectbox("Select book", list(options.keys()))
                borrower_name = st.text_input("Borrower's name")
                borrow_date = st.date_input("Borrow date", value=date.today())
                due_date = st.date_input("Due date", value=date.today() + timedelta(days=14))
                submitted = st.form_submit_button("Confirm borrowing")

                if submitted:
                    if not borrower_name.strip():
                        st.error("Enter the borrower's name.")
                    elif due_date < borrow_date:
                        st.error("Due date cannot be before borrow date.")
                    else:
                        try:
                            with connect() as conn:
                                count = conn.execute(
                                    "SELECT total_copies FROM books WHERE id=?",
                                    (options[selected_label],),
                                ).fetchone()
                                borrowed = conn.execute(
                                    "SELECT COUNT(*) AS n FROM loans WHERE book_id=? AND return_date IS NULL",
                                    (options[selected_label],),
                                ).fetchone()["n"]
                                if count is None or borrowed >= count["total_copies"]:
                                    st.error("No copies of this book are currently available.")
                                else:
                                    conn.execute(
                                        """
                                        INSERT INTO loans
                                        (book_id, user_id, borrow_date, due_date, return_date)
                                        VALUES (?, ?, ?, ?, NULL)
                                        """,
                                        (
                                            options[selected_label],
                                            borrower_name.strip(),
                                            borrow_date.isoformat(),
                                            due_date.isoformat(),
                                        ),
                                    )
                                    st.session_state["success_message"] = "Book borrowed successfully."
                                    st.rerun()
                        except sqlite3.Error as exc:
                            st.error(f"Borrowing failed: {exc}")

    with return_tab:
        if active_loans.empty:
            st.info("There are no active loans to return.")
        else:
            return_options = {
                f'Loan #{int(row.loan_id)} — {row.title} — {row.user_id}': int(row.loan_id)
                for row in active_loans.itertuples()
            }
            with st.form("return_form"):
                selected_loan = st.selectbox("Select active loan", list(return_options.keys()))
                return_date = st.date_input("Return date", value=date.today())
                submitted_return = st.form_submit_button("Confirm return")

                if submitted_return:
                    try:
                        with connect() as conn:
                            conn.execute(
                                "UPDATE loans SET return_date=? WHERE id=? AND return_date IS NULL",
                                (return_date.isoformat(), return_options[selected_loan]),
                            )
                        st.session_state["success_message"] = "Book returned successfully."
                        st.rerun()
                    except sqlite3.Error as exc:
                        st.error(f"Return failed: {exc}")

    with history_tab:
        if loans.empty:
            st.info("No loan records found.")
        else:
            history = loans.copy()
            history["status"] = history["return_date"].apply(
                lambda value: "Returned" if pd.notna(value) else "Borrowed"
            )
            st.dataframe(history, use_container_width=True, hide_index=True)

# --------------------------------------------------
# Analytics
# --------------------------------------------------
elif page == "Analytics":
    st.subheader("📊 Historical Borrowing Analytics")
    st.info(
        "This section uses the historical CSV dataset, which is separate from "
        "current physical inventory in the SQLite database."
    )

    if not DATA_FILE.exists():
        st.warning(f"Historical dataset not found: {DATA_FILE}")
    else:
        try:
            df = pd.read_csv(DATA_FILE)
            st.metric("Historical records", f"{len(df):,}")

            date_column = next(
                (col for col in ["borrow_date", "borrowed_date", "date"] if col in df.columns),
                None,
            )
            category_column = next(
                (col for col in ["book_category", "category"] if col in df.columns),
                None,
            )

            left, right = st.columns(2)
            with left:
                if category_column:
                    st.markdown("#### Records by category")
                    st.bar_chart(df[category_column].fillna("Unknown").value_counts())
                else:
                    st.info("No category column found in the historical dataset.")

            with right:
                if date_column:
                    dates = pd.to_datetime(df[date_column], errors="coerce")
                    trend = dates.dropna().dt.to_period("M").astype(str).value_counts().sort_index()
                    st.markdown("#### Borrowing activity over time")
                    st.line_chart(trend)
                else:
                    st.info("No borrowing-date column found in the historical dataset.")

            st.markdown("#### Historical records")
            st.dataframe(df, use_container_width=True, hide_index=True)
        except Exception as exc:
            st.error(f"Could not load historical analytics: {exc}")
