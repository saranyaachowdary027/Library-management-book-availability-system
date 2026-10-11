
import streamlit as st
import pandas as pd
from pathlib import Path

# Page settings
st.set_page_config(
    page_title="Library Book Availability",
    page_icon="📚",
    layout="wide"
)

# Project paths
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_FILE = BASE_DIR / "data" / "processed" / "library_datasets_cleaned.csv"

# Dashboard heading
st.title("📚 Library Book Availability Dashboard")
st.write("Explore library records and book availability.")

# Load dataset
@st.cache_data
def load_data(path):
    return pd.read_csv(path)

if not DATA_FILE.exists():
    st.error(f"Dataset not found: {DATA_FILE}")
    st.info(
        "Please check that library_datasets_cleaned.csv "
        "is inside data/processed/"
    )
    st.stop()

df = load_data(DATA_FILE)

# Sidebar filters
st.sidebar.header("Filters")
st.sidebar.write("Choose a column to filter the records.")

filtered_df = df.copy()

filter_column = st.sidebar.selectbox(
    "Select a column",
    ["None"] + df.columns.tolist()
)

if filter_column != "None":
    values = sorted(
        df[filter_column].dropna().astype(str).unique().tolist()
    )
    selected_values = st.sidebar.multiselect(
        f"Select {filter_column} values",
        values,
        default=values
    )
    filtered_df = filtered_df[
        filtered_df[filter_column].astype(str).isin(selected_values)
    ]

# Summary metrics
col1, col2 = st.columns(2)

with col1:
    st.metric("Total Records", len(filtered_df))

with col2:
    st.metric("Total Columns", len(filtered_df.columns))

# Dataset preview
st.subheader("📋 Library Records")
st.dataframe(filtered_df, use_container_width=True)

# Column summary
st.subheader("📊 Explore a Column")
if len(df.columns) > 0:
    chart_column = st.selectbox(
        "Choose a column for the chart",
        df.columns.tolist(),
        key="chart_column"
    )

    chart_data = (
        filtered_df[chart_column]
        .fillna("Missing")
        .astype(str)
        .value_counts()
        .head(15)
    )

    if not chart_data.empty:
        st.bar_chart(chart_data)
    else:
        st.info("No records match the selected filters.")

# Download filtered data
st.subheader("⬇️ Download Records")
csv_data = filtered_df.to_csv(index=False).encode("utf-8")

st.download_button(
    label="Download filtered CSV",
    data=csv_data,
    file_name="library_filtered_data.csv",
    mime="text/csv"
)
