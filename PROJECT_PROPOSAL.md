# Project Proposal: Library Management Book Availability System

## Problem

Library staff and readers need a clear way to find books, review borrowing and
reservation activity, and check whether copies are currently available. The
project combines a borrowing dataset with the project's SQLite inventory and
loan records to support analysis and an interactive dashboard.

## Objectives

- Preserve the source dataset and provide a repeatable cleaning workflow.
- Summarize borrowing, reservation, overdue, and book-category records.
- Create charts that make these patterns easy to review.
- Provide an interactive dashboard for inventory and book-availability tasks.

## Data

The raw CSV is stored at `data/raw/library_datasets.csv`. Its fields include
user and book IDs, borrow and return dates, reservation and overdue status,
user role, and book category. The cleaned CSV is stored at
`data/processed/library_datasets_cleaned.csv`. The application also uses the
project's SQLite database (`library.db`) for book inventory and loan records.

The event dataset alone does not represent live stock. Availability shown by
the application should be based on the inventory and active-loan records in
the database.

## Method

1. Keep the raw CSV unchanged and document its source.
2. Use `data_cleaning.py` to standardize values, dates, and exact duplicate
   records, then write the processed CSV.
3. Use `Data_analysis.py` to summarize the cleaned records.
4. Use `Data_visualisation.py` to save charts under `reports/`.
5. Use the interactive dashboard source under `dashboard/` and its supporting
   database/API code to explore inventory and availability.

## Tools

Python, pandas, Matplotlib, Streamlit, FastAPI, SQLite, Visual Studio Code, and
GitHub.

## Expected outcome

The project will provide reproducible dataset preparation, clear analysis and
visualizations, and an interactive prototype for reviewing book availability.
It is a course project prototype; production deployment and live integration
with an external library system are outside the current scope.
