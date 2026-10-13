
import streamlit as st
import pandas as pd
from pathlib import Path

# --------------------------------------------------
# 1. PAGE SETTINGS
# --------------------------------------------------
st.set_page_config(
    page_title="Library Management Dashboard",
    page_icon="📚",
    layout="wide"
)

# --------------------------------------------------
# 2. DATASET PATH
# --------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_FILE = (
    BASE_DIR
    / "data"
    / "processed"
    / "library_datasets_cleaned.csv"
)

# --------------------------------------------------
# 3. LOAD DATA
# --------------------------------------------------
@st.cache_data
def load_data(path):
    data = pd.read_csv(path)

    # Standardize column names
    data.columns = data.columns.str.strip().str.lower()

    # Convert dates safely
    for column in ["borrow_date", "return_date"]:
        if column in data.columns:
            data[column] = pd.to_datetime(
                data[column], errors="coerce"
            )

    # Normalize Boolean/status values
    if "reservation_status" in data.columns:
        data["reservation_status"] = (
            data["reservation_status"]
            .astype("string")
            .str.strip()
            .str.lower()
            .map({
                "true": "Reserved",
                "false": "Not Reserved",
                "1": "Reserved",
                "0": "Not Reserved",
                "reserved": "Reserved",
                "not reserved": "Not Reserved"
            })
            .fillna("Unknown")
        )

    if "overdue_status" in data.columns:
        data["overdue_status"] = pd.to_numeric(
            data["overdue_status"], errors="coerce"
        )

    if "borrow_duration_days" in data.columns:
        data["borrow_duration_days"] = pd.to_numeric(
            data["borrow_duration_days"], errors="coerce"
        )

    return data


st.title("📚 Library Management Dashboard")
st.write(
    "Explore book records, borrowing activity, "
    "reservation status, and overdue records in one place."
)

if not DATA_FILE.exists():
    st.error(f"Dataset not found: {DATA_FILE}")
    st.info(
        "Check that library_datasets_cleaned.csv is inside "
        "the data/processed folder."
    )
    st.stop()

try:
    df = load_data(str(DATA_FILE))
except Exception as error:
    st.error(f"Unable to load the dataset: {error}")
    st.stop()

if df.empty:
    st.warning("The dataset has no records.")
    st.stop()

# Verify essential fields
required_columns = ["book_id", "user_id"]
missing_columns = [
    column for column in required_columns
    if column not in df.columns
]

if missing_columns:
    st.error(
        "Required dataset columns are missing: "
        + ", ".join(missing_columns)
    )
    st.stop()

# --------------------------------------------------
# 4. SIDEBAR FILTERS
# --------------------------------------------------
st.sidebar.header("🔎 Find and Filter Records")

search_text = st.sidebar.text_input(
    "Search book ID or user ID",
    placeholder="Enter an ID or keyword"
)

filtered_df = df.copy()

if search_text.strip():
    search = search_text.strip()

    book_match = filtered_df["book_id"].astype(
        "string"
    ).str.contains(search, case=False, na=False, regex=False)

    user_match = filtered_df["user_id"].astype(
        "string"
    ).str.contains(search, case=False, na=False, regex=False)

    filtered_df = filtered_df[book_match | user_match]


def add_category_filter(data, column, label):
    if column in data.columns:
        options = sorted(
            data[column].dropna().astype(str).unique().tolist()
        )
        selected = st.sidebar.multiselect(
            label, options, default=options
        )

        if selected:
            return data[data[column].astype(str).isin(selected)]

        return data.iloc[0:0]

    return data


filtered_df = add_category_filter(
    filtered_df, "book_category", "Book category"
)

filtered_df = add_category_filter(
    filtered_df, "user_role", "User role"
)

filtered_df = add_category_filter(
    filtered_df, "reservation_status", "Reservation status"
)

if "overdue_status" in filtered_df.columns:
    overdue_filter = st.sidebar.selectbox(
        "Overdue status",
        [
            "All records",
            "Overdue only",
            "Not overdue only"
        ]
    )

    if overdue_filter == "Overdue only":
        filtered_df = filtered_df[
            filtered_df["overdue_status"] == 1
        ]
    elif overdue_filter == "Not overdue only":
        filtered_df = filtered_df[
            filtered_df["overdue_status"] == 0
        ]

if st.sidebar.button("Reset all filters"):
    st.cache_data.clear()
    st.rerun()

# --------------------------------------------------
# 5. DASHBOARD SUMMARY CARDS
# --------------------------------------------------
st.subheader("📊 Library Overview")

total_records = len(filtered_df)
unique_books = filtered_df["book_id"].nunique()
unique_users = filtered_df["user_id"].nunique()

if "overdue_status" in filtered_df.columns:
    overdue_count = int(
        (filtered_df["overdue_status"] == 1).sum()
    )
else:
    overdue_count = 0

if "reservation_status" in filtered_df.columns:
    reserved_count = int(
        (filtered_df["reservation_status"] == "Reserved").sum()
    )
else:
    reserved_count = 0

c1, c2, c3 = st.columns(3)
c1.metric("Borrowing Records", f"{total_records:,}")
c2.metric("Unique Book IDs", f"{unique_books:,}")
c3.metric("Unique Users", f"{unique_users:,}")

c4, c5, c6 = st.columns(3)
c4.metric("Overdue Records", f"{overdue_count:,}")
c5.metric("Reserved Records", f"{reserved_count:,}")

if "borrow_duration_days" in filtered_df.columns:
    avg_duration = filtered_df["borrow_duration_days"].mean()
    duration_label = (
        f"{avg_duration:.1f} days"
        if pd.notna(avg_duration)
        else "No data"
    )
else:
    duration_label = "No data"

c6.metric("Average Borrow Duration", duration_label)

st.info(
    "This dashboard summarizes borrowing records. "
    "A book ID represents a record identifier, not a book title. "
    "This dataset does not confirm current physical availability."
)

# --------------------------------------------------
# 6. BORROWING RECORDS TABLE
# --------------------------------------------------
st.subheader("📋 Borrowing and Book Records")

if filtered_df.empty:
    st.warning(
        "No matching records found. Try changing your search "
        "or filters."
    )
else:
    display_df = filtered_df.copy()

    # Make dates easier to read
    for column in ["borrow_date", "return_date"]:
        if column in display_df.columns:
            display_df[column] = display_df[column].dt.strftime(
                "%Y-%m-%d"
            ).fillna("Unknown")

    st.caption(
        f"Showing {len(display_df):,} matching records."
    )

    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True
    )

# --------------------------------------------------
# 7. OVERDUE SUMMARY
# --------------------------------------------------
st.subheader("⏰ Overdue Record Summary")

if "overdue_status" in filtered_df.columns:
    overdue_summary = (
        filtered_df["overdue_status"]
        .map({1: "Overdue", 0: "Not Overdue"})
        .fillna("Unknown")
        .value_counts()
    )

    if not overdue_summary.empty:
        st.bar_chart(overdue_summary)
    else:
        st.info("No overdue information is available.")
else:
    st.info("The dataset has no overdue status column.")

# --------------------------------------------------
# 8. BOOK CATEGORY SUMMARY
# --------------------------------------------------
st.subheader("📚 Records by Book Category")

if "book_category" in filtered_df.columns:
    category_summary = (
        filtered_df["book_category"]
        .fillna("Unknown")
        .value_counts()
    )

    if not category_summary.empty:
        st.bar_chart(category_summary)
    else:
        st.info("No category information is available.")
else:
    st.info("The dataset has no book category column.")

# --------------------------------------------------
# 9. RESERVATION SUMMARY
# --------------------------------------------------
st.subheader("🗓️ Reservation Status")

if "reservation_status" in filtered_df.columns:
    reservation_summary = (
        filtered_df["reservation_status"]
        .fillna("Unknown")
        .value_counts()
    )

    if not reservation_summary.empty:
        st.bar_chart(reservation_summary)
    else:
        st.info("No reservation information is available.")
else:
    st.info("The dataset has no reservation status column.")

# --------------------------------------------------
# 10. BORROWING TREND
# --------------------------------------------------
st.subheader("📈 Borrowing Activity Over Time")

if "borrow_date" in filtered_df.columns:
    trend_data = filtered_df.dropna(subset=["borrow_date"]).copy()

    if not trend_data.empty:
        trend_data["Month"] = (
            trend_data["borrow_date"].dt.to_period("M").astype(str)
        )

        monthly_borrowing = (
            trend_data.groupby("Month")
            .size()
            .sort_index()
        )

        st.line_chart(monthly_borrowing)
    else:
        st.info("No valid borrowing dates are available.")
else:
    st.info("The dataset has no borrowing date column.")

# --------------------------------------------------
# 11. BORROWING DURATION
# --------------------------------------------------
st.subheader("📅 Borrowing Duration")

if "borrow_duration_days" in filtered_df.columns:
    duration_data = filtered_df[
        "borrow_duration_days"
    ].dropna()

    if not duration_data.empty:
        duration_counts = (
            duration_data.round()
            .astype(int)
            .value_counts()
            .sort_index()
        )

        st.bar_chart(duration_counts)
        st.caption(
            "This chart shows how frequently each borrowing "
            "duration appears in the records."
        )
    else:
        st.info("No borrowing duration values are available.")
else:
    st.info("The dataset has no borrowing duration column.")

# --------------------------------------------------
# 12. DOWNLOAD FILTERED RECORDS
# --------------------------------------------------
st.subheader("⬇️ Download Records")

csv_data = filtered_df.to_csv(index=False).encode("utf-8")

st.download_button(
    label="Download filtered records as CSV",
    data=csv_data,
    file_name="library_filtered_records.csv",
    mime="text/csv"
)

# --------------------------------------------------
# 13. PROJECT LIMITATION
# --------------------------------------------------
with st.expander("ℹ️ About this dashboard"):
    st.write(
        "The current dataset contains book IDs and borrowing "
        "records, including reservation status, overdue status, "
        "book category, and borrowing dates."
    )
    st.write(
        "It does not include book titles, author names, or a "
        "confirmed inventory availability field. To search by "
        "title or author and confirm whether a physical copy is "
        "available, integrate a reliable book catalogue and "
        "current inventory or active-loan data."
    )
