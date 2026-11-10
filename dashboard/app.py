import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from datetime import date, timedelta

import pandas as pd
import streamlit as st
from sqlalchemy import create_engine, event, inspect, text
from sqlalchemy.engine import URL, make_url
from sqlalchemy.exc import SQLAlchemyError

# -------------------- CONFIG --------------------
BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "library.db"
DATA_FILE = BASE_DIR / "data" / "processed" / "library_datasets_cleaned.csv"

st.set_page_config(
    page_title="Library Management",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded",
)


def secret(name):
    try:
        return st.secrets[name]
    except Exception:
        return os.environ.get(name)


DATABASE_URL = secret("DATABASE_URL")
APP_PASSWORD = secret("APP_PASSWORD")
REMOTE_DATABASE = bool(DATABASE_URL)

if DATABASE_URL:
    db_url = make_url(DATABASE_URL)
    if db_url.drivername in {"postgres", "postgresql"}:
        db_url = db_url.set(drivername="postgresql+psycopg")
    ENGINE = create_engine(
        db_url,
        pool_pre_ping=True,
        pool_size=2,
        max_overflow=0,
        connect_args={"sslmode": "require"} if db_url.drivername.startswith("postgresql") else {},
    )
else:
    ENGINE = create_engine(
        URL.create("sqlite", database=str(DB_PATH)),
        connect_args={"check_same_thread": False},
    )


if ENGINE.dialect.name == "sqlite":
    @event.listens_for(ENGINE, "connect")
    def enable_sqlite_foreign_keys(dbapi_connection, _connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


@contextmanager
def connect():
    with ENGINE.begin() as conn:
        yield conn


def initialize_database():
    if REMOTE_DATABASE:
        with connect() as conn:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS books (
                    id BIGSERIAL PRIMARY KEY,
                    isbn TEXT UNIQUE,
                    title TEXT NOT NULL,
                    author TEXT NOT NULL,
                    category TEXT,
                    total_copies INTEGER NOT NULL DEFAULT 1
                        CHECK (total_copies >= 0)
                )
            """))
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS loans (
                    id BIGSERIAL PRIMARY KEY,
                    book_id BIGINT NOT NULL REFERENCES books(id),
                    user_id TEXT NOT NULL,
                    borrow_date TEXT NOT NULL,
                    due_date TEXT NOT NULL,
                    return_date TEXT DEFAULT NULL
                )
            """))

            book_count = conn.execute(text("SELECT COUNT(*) FROM books")).scalar_one()
            loan_count = conn.execute(text("SELECT COUNT(*) FROM loans")).scalar_one()

            # Seed an empty hosted database once from the project's included SQLite snapshot.
            if book_count == 0 and loan_count == 0 and DB_PATH.exists():
                with sqlite3.connect(DB_PATH) as source:
                    source.row_factory = sqlite3.Row
                    books = source.execute("SELECT id,isbn,title,author,category,total_copies FROM books").fetchall()
                    loans = source.execute("SELECT id,book_id,user_id,borrow_date,due_date,return_date FROM loans").fetchall()
                for book in books:
                    conn.execute(text("""
                        INSERT INTO books (id,isbn,title,author,category,total_copies)
                        VALUES (:id,:isbn,:title,:author,:category,:total_copies)
                        ON CONFLICT (id) DO NOTHING
                    """), dict(book))
                for loan in loans:
                    conn.execute(text("""
                        INSERT INTO loans (id,book_id,user_id,borrow_date,due_date,return_date)
                        VALUES (:id,:book_id,:user_id,:borrow_date,:due_date,:return_date)
                        ON CONFLICT (id) DO NOTHING
                    """), dict(loan))
                conn.execute(text("""
                    SELECT setval(pg_get_serial_sequence('books','id'),
                        GREATEST(COALESCE((SELECT MAX(id) FROM books),0)+1,1), false)
                """))
                conn.execute(text("""
                    SELECT setval(pg_get_serial_sequence('loans','id'),
                        GREATEST(COALESCE((SELECT MAX(id) FROM loans),0)+1,1), false)
                """))

if REMOTE_DATABASE:
    if not APP_PASSWORD:
        st.error("Hosted editing is locked until APP_PASSWORD is configured in the app's private secrets.")
        st.stop()
    if not st.session_state.get("staff_authenticated"):
        st.title("Library staff sign-in")
        entered_password = st.text_input("Staff password", type="password")
        if st.button("Sign in"):
            if entered_password == APP_PASSWORD:
                st.session_state["staff_authenticated"] = True
                st.rerun()
            st.error("Incorrect password.")
        st.stop()

st.markdown("""
<style>
.stApp {background:#f4f6fb;color:#172033}
.block-container {padding-top:1.4rem;max-width:1500px}
[data-testid="stSidebar"] {background:#111a31}
[data-testid="stSidebar"] * {color:#f5f7ff}
[data-testid="stMetric"] {
    background:white;
    border:1px solid #e4e8f2;
    border-radius:14px;
    padding:16px;
    box-shadow:0 3px 12px #1923460d
}
[data-testid="stMetricLabel"] {color:#64748b}
[data-testid="stMetricValue"] {color:#172033;font-weight:750}
.stButton>button,.stFormSubmitButton>button {
    background:#7048e8;
    color:white;
    border:0;
    border-radius:9px;
    min-height:40px;
    font-weight:600
}
.stButton>button:hover,.stFormSubmitButton>button:hover {
    background:#5b35cc;
    color:white
}
</style>
""", unsafe_allow_html=True)


def load_books():
    with connect() as conn:
        return pd.read_sql_query(text("""
            SELECT
                b.id AS book_id,
                b.title,
                b.author,
                b.category,
                b.total_copies,
                MAX(0, b.total_copies - (
                    SELECT COUNT(*)
                    FROM loans l
                    WHERE l.book_id = b.id
                      AND l.return_date IS NULL
                )) AS available_copies
            FROM books b
            ORDER BY b.title
        """), conn)


def load_loans():
    with connect() as conn:
        return pd.read_sql_query(text("""
            SELECT
                l.id AS loan_id,
                l.book_id,
                b.title,
                b.author,
                l.user_id,
                l.borrow_date,
                l.due_date,
                l.return_date
            FROM loans l
            LEFT JOIN books b ON b.id = l.book_id
            ORDER BY l.id DESC
        """), conn)


def validate_database():
    initialize_database()
    inspector = inspect(ENGINE)
    with connect() as conn:
        tables = set(inspector.get_table_names())

        if not {"books", "loans"}.issubset(tables):
            raise RuntimeError(
                "The database must contain 'books' and 'loans' tables."
            )

        book_cols = {c["name"] for c in inspector.get_columns("books")}

        loan_cols = {c["name"] for c in inspector.get_columns("loans")}

        required_books = {
            "id", "title", "author", "category", "total_copies"
        }

        required_loans = {
            "id", "book_id", "user_id",
            "borrow_date", "due_date", "return_date"
        }

        if not required_books.issubset(book_cols):
            raise RuntimeError(
                f"Unexpected books columns: {sorted(book_cols)}"
            )

        if not required_loans.issubset(loan_cols):
            raise RuntimeError(
                f"Unexpected loans columns: {sorted(loan_cols)}"
            )


# -------------------- NAVIGATION --------------------
pages = [
    "Overview",
    "Live Inventory",
    "Catalogue",
    "Add a Book",
    "Borrow & Return",
    "Analytics",
]

if "main_navigation" not in st.session_state:
    st.session_state["main_navigation"] = "Overview"

with st.sidebar:
    st.markdown("# 📚 LIBRARY")
    st.caption("Management workspace")
    st.divider()

    page = st.radio(
        "NAVIGATION",
        pages,
        key="main_navigation",
    )

    st.divider()
    st.caption("Library Management System")


# -------------------- PAGE HEADER --------------------
st.title("📚 Library Management")
st.caption(
    "Monitor inventory, manage circulation, and explore library activity."
)

# Keep success messages visible after a rerun.
if st.session_state.get("success_message"):
    st.success(st.session_state["success_message"])

    if st.button("Dismiss message", key="dismiss_success"):
        del st.session_state["success_message"]
        st.rerun()


# -------------------- LOAD DATA --------------------
try:
    validate_database()
    books = load_books()
    loans = load_loans()

except Exception as exc:
    st.error(f"Could not load the library database: {exc}")
    st.info("Check the app's database configuration and deployment secrets.")
    st.stop()


active_loans = (
    loans[loans["return_date"].isna()].copy()
    if not loans.empty
    else loans.copy()
)

total_titles = len(books)

total_copies = (
    int(books["total_copies"].fillna(0).sum())
    if not books.empty else 0
)

available_copies = (
    int(books["available_copies"].fillna(0).sum())
    if not books.empty else 0
)

borrowed_copies = len(active_loans)
overdue_count = 0

if not active_loans.empty:
    due_dates = pd.to_datetime(
        active_loans["due_date"],
        errors="coerce",
    )
    overdue_count = int(
        (due_dates.dt.date < date.today()).sum()
    )


# -------------------- OVERVIEW --------------------
if page == "Overview":
    st.subheader("Overview")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Book titles", total_titles)
    c2.metric("Total copies", total_copies)
    c3.metric("Available copies", available_copies)
    c4.metric("Currently borrowed", borrowed_copies)

    left, right = st.columns([1.5, 1])

    with left:
        st.subheader("📈 Collection availability")

        if books.empty:
            st.info("No books are in the catalogue yet.")
        else:
            st.bar_chart(
                books.set_index("title")[
                    ["available_copies", "total_copies"]
                ]
            )

    with right:
        st.subheader("⏰ Circulation status")
        st.metric("Overdue loans", overdue_count)

        st.metric(
            "Titles with no copies available",
            int((books["available_copies"] == 0).sum())
            if not books.empty else 0,
        )

        st.metric("Active loans", borrowed_copies)

    st.subheader("📋 Current inventory")
    st.dataframe(
        books,
        use_container_width=True,
        hide_index=True,
    )

    st.subheader("⚡ Quick actions")

    a, b, c = st.columns(3)

    if a.button("📚 Browse catalogue", use_container_width=True):
        st.session_state["main_navigation"] = "Catalogue"
        st.rerun()

    if b.button("➕ Borrow a book", use_container_width=True):
        st.session_state["main_navigation"] = "Borrow & Return"
        st.rerun()

    if c.button("📦 View inventory", use_container_width=True):
        st.session_state["main_navigation"] = "Live Inventory"
        st.rerun()


# -------------------- LIVE INVENTORY --------------------
elif page == "Live Inventory":
    st.subheader("📦 Live Inventory")

    search = st.text_input(
        "Search by title, author, or category",
        key="inventory_search",
    )

    result = books.copy()

    if search.strip() and not result.empty:
        mask = (
            result[["title", "author", "category"]]
            .fillna("")
            .astype(str)
            .apply(
                lambda col: col.str.contains(
                    search.strip(),
                    case=False,
                    regex=False,
                )
            )
            .any(axis=1)
        )

        result = result[mask]

    a, b, c = st.columns(3)

    a.metric("Titles", len(result))

    b.metric(
        "Available copies",
        int(result["available_copies"].sum())
        if not result.empty else 0,
    )

    c.metric(
        "Unavailable copies",
        int(
            (
                result["total_copies"]
                - result["available_copies"]
            ).clip(lower=0).sum()
        ) if not result.empty else 0,
    )

    st.dataframe(
        result,
        use_container_width=True,
        hide_index=True,
    )


# -------------------- CATALOGUE --------------------
elif page == "Catalogue":
    st.subheader("📖 Book Catalogue")

    search = st.text_input(
        "Search catalogue",
        placeholder="Title, author, or category",
        key="catalogue_search",
    )

    result = books.copy()

    if search.strip() and not result.empty:
        mask = (
            result[["title", "author", "category"]]
            .fillna("")
            .astype(str)
            .apply(
                lambda col: col.str.contains(
                    search.strip(),
                    case=False,
                    regex=False,
                )
            )
            .any(axis=1)
        )

        result = result[mask]

    st.dataframe(
        result,
        use_container_width=True,
        hide_index=True,
    )


# -------------------- BORROW & RETURN --------------------
elif page == "Add a Book":
    st.subheader("➕ Add a Book")
    st.caption("Add a title and copy count to the shared library catalogue.")
    with st.form("add_book_form", clear_on_submit=True):
        title = st.text_input("Book title")
        author = st.text_input("Author")
        category = st.text_input("Category")
        isbn = st.text_input("ISBN (optional)")
        copies = st.number_input("Total copies", min_value=0, value=1, step=1)
        submitted_book = st.form_submit_button("Save book")
        if submitted_book:
            if not title.strip() or not author.strip():
                st.error("Enter both a title and an author.")
            else:
                try:
                    with connect() as conn:
                        conn.execute(text("""
                            INSERT INTO books (isbn,title,author,category,total_copies)
                            VALUES (:isbn,:title,:author,:category,:total_copies)
                        """), {
                            "isbn": isbn.strip() or None,
                            "title": title.strip(),
                            "author": author.strip(),
                            "category": category.strip() or None,
                            "total_copies": int(copies),
                        })
                    st.session_state["success_message"] = "Book added to the catalogue."
                    st.rerun()
                except SQLAlchemyError as exc:
                    st.error(f"Could not add the book. Check that its ISBN is unique. Details: {exc}")

# -------------------- BORROW & RETURN --------------------
elif page == "Borrow & Return":
    st.subheader("🔄 Borrow & Return")

    st.caption(
        "Borrowing and return records are stored in your existing database."
    )

    available_books = books[
        books["available_copies"] > 0
    ].copy()

    borrow_tab, return_tab, history_tab = st.tabs([
        "➕ Borrow a book",
        "↩️ Return a book",
        "📋 Loan history",
    ])

    # BORROW BOOK
    with borrow_tab:
        if available_books.empty:
            st.warning(
                "No books are currently available to borrow."
            )

        else:
            options = {
                (
                    f"{r.title} — {r.author} "
                    f"({int(r.available_copies)} available)"
                ): int(r.book_id)
                for r in available_books.itertuples()
            }

            with st.form(
                "borrow_form",
                clear_on_submit=True,
            ):
                selected_label = st.selectbox(
                    "Select book",
                    list(options.keys()),
                )

                borrower_name = st.text_input(
                    "Borrower's name"
                )

                borrow_date = st.date_input(
                    "Borrow date",
                    value=date.today(),
                )

                due_date = st.date_input(
                    "Due date",
                    value=date.today() + timedelta(days=14),
                )

                submitted = st.form_submit_button(
                    "Confirm borrowing"
                )

                if submitted:
                    if not borrower_name.strip():
                        st.error("Enter the borrower's name.")

                    elif due_date < borrow_date:
                        st.error(
                            "Due date cannot be before borrow date."
                        )

                    else:
                        try:
                            with connect() as conn:
                                book = conn.execute(
                                    text("""
                                    SELECT total_copies
                                    FROM books
                                    WHERE id=:book_id
                                    """),
                                    {"book_id": options[selected_label]},
                                ).mappings().first()

                                active_count = conn.execute(
                                    text("""
                                    SELECT COUNT(*)
                                    FROM loans
                                    WHERE book_id=:book_id
                                      AND return_date IS NULL
                                    """),
                                    {"book_id": options[selected_label]},
                                ).scalar_one()

                                if (
                                    book is None
                                    or active_count >= book["total_copies"]
                                ):
                                    st.error(
                                        "No copies of this book are "
                                        "currently available."
                                    )

                                else:
                                    conn.execute(
                                        text("""
                                        INSERT INTO loans
                                        (
                                            book_id,
                                            user_id,
                                            borrow_date,
                                            due_date,
                                            return_date
                                        )
                                        VALUES (:book_id, :user_id, :borrow_date, :due_date, NULL)
                                        """),
                                        {
                                            "book_id": options[selected_label],
                                            "user_id": borrower_name.strip(),
                                            "borrow_date": borrow_date.isoformat(),
                                            "due_date": due_date.isoformat(),
                                        },
                                    )

                                    st.session_state[
                                        "success_message"
                                    ] = "Book borrowed successfully."

                                    st.rerun()

                        except (sqlite3.Error, SQLAlchemyError) as exc:
                            st.error(f"Borrowing failed: {exc}")

    # RETURN BOOK
    with return_tab:
        if active_loans.empty:
            st.info(
                "There are no active loans to return."
            )

        else:
            return_options = {
                (
                    f"Loan #{int(r.loan_id)} — "
                    f"{r.title} — {r.user_id}"
                ): int(r.loan_id)
                for r in active_loans.itertuples()
            }

            with st.form("return_form"):
                selected_loan = st.selectbox(
                    "Select active loan",
                    list(return_options.keys()),
                )

                return_date = st.date_input(
                    "Return date",
                    value=date.today(),
                )

                submitted_return = st.form_submit_button(
                    "Confirm return"
                )

                if submitted_return:
                    try:
                        with connect() as conn:
                            conn.execute(
                                text("""
                                UPDATE loans
                                SET return_date=:return_date
                                WHERE id=:loan_id
                                  AND return_date IS NULL
                                """),
                                {
                                    "return_date": return_date.isoformat(),
                                    "loan_id": return_options[selected_loan],
                                },
                            )

                        st.session_state[
                            "success_message"
                        ] = "Book returned successfully."

                        st.rerun()

                    except (sqlite3.Error, SQLAlchemyError) as exc:
                        st.error(f"Return failed: {exc}")

    # LOAN HISTORY
    with history_tab:
        if loans.empty:
            st.info("No loan records found.")

        else:
            history = loans.copy()

            history["status"] = history["return_date"].apply(
                lambda value:
                    "Returned" if pd.notna(value) else "Borrowed"
            )

            st.dataframe(
                history,
                use_container_width=True,
                hide_index=True,
            )


# -------------------- ANALYTICS --------------------
elif page == "Analytics":
    st.subheader("📊 Historical Borrowing Analytics")

    st.info(
        "Historical CSV analytics are separate from the current "
        "SQLite inventory."
    )

    if not DATA_FILE.exists():
        st.warning(
            f"Historical dataset not found: {DATA_FILE}"
        )

    else:
        try:
            df = pd.read_csv(DATA_FILE)

            st.metric(
                "Historical records",
                len(df),
            )

            date_col = next(
                (
                    c for c in [
                        "borrow_date",
                        "borrowed_date",
                        "date",
                    ]
                    if c in df.columns
                ),
                None,
            )

            category_col = next(
                (
                    c for c in [
                        "book_category",
                        "category",
                    ]
                    if c in df.columns
                ),
                None,
            )

            left, right = st.columns(2)

            with left:
                if category_col:
                    st.markdown("#### Records by category")

                    st.bar_chart(
                        df[category_col]
                        .fillna("Unknown")
                        .value_counts()
                    )

                else:
                    st.info(
                        "No category column found in the historical dataset."
                    )

            with right:
                if date_col:
                    dates = pd.to_datetime(
                        df[date_col],
                        errors="coerce",
                    )

                    trend = (
                        dates.dropna()
                        .dt.to_period("M")
                        .astype(str)
                        .value_counts()
                        .sort_index()
                    )

                    st.markdown(
                        "#### Borrowing activity over time"
                    )

                    st.line_chart(trend)

                else:
                    st.info(
                        "No borrowing-date column found in the historical dataset."
                    )

            st.markdown("#### Historical records")

            st.dataframe(
                df,
                use_container_width=True,
                hide_index=True,
            )

        except Exception as exc:
            st.error(
                f"Could not load historical analytics: {exc}"
            )
