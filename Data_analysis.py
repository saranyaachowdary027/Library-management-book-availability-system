"""Summarize borrowing, reservation, overdue, and category data."""

from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parent
DATA_FILE = PROJECT_ROOT / "data" / "processed" / "library_datasets_cleaned.csv"
REPORT_FILE = PROJECT_ROOT / "reports" / "data_analysis_summary.txt"


def main() -> None:
    if not DATA_FILE.is_file():
        raise FileNotFoundError(
            f"Cleaned dataset not found: {DATA_FILE}. Run data_cleaning.py first."
        )

    data = pd.read_csv(DATA_FILE)
    for column in ("borrow_date", "return_date"):
        if column in data.columns:
            data[column] = pd.to_datetime(data[column], errors="coerce")

    lines = [
        "LIBRARY MANAGEMENT BOOK AVAILABILITY SYSTEM — DATA ANALYSIS",
        "",
        f"Records: {len(data)}",
        f"Columns: {len(data.columns)}",
    ]

    if "book_id" in data.columns:
        lines.append(f"Distinct book IDs: {data['book_id'].nunique(dropna=True)}")
    if "user_id" in data.columns:
        lines.append(f"Distinct user IDs: {data['user_id'].nunique(dropna=True)}")

    if "book_category" in data.columns:
        lines.extend(["", "Records by book category:"])
        lines.extend(
            f"  {label}: {count}"
            for label, count in data["book_category"].value_counts(dropna=False).items()
        )

    if "reservation_status" in data.columns:
        lines.extend(["", "Reservation status counts:"])
        lines.extend(
            f"  {label}: {count}"
            for label, count in data["reservation_status"].value_counts(dropna=False).items()
        )

    if "overdue_status" in data.columns:
        overdue = pd.to_numeric(data["overdue_status"], errors="coerce")
        lines.extend(
            [
                "",
                "Overdue status:",
                f"  Records marked overdue (value 1): {int((overdue == 1).sum())}",
                f"  Records with a usable overdue value: {int(overdue.notna().sum())}",
            ]
        )

    if {"borrow_date", "return_date"}.issubset(data.columns):
        duration = (data["return_date"] - data["borrow_date"]).dt.days.dropna()
        lines.extend(["", "Borrowing duration (returned loans only):"])
        if duration.empty:
            lines.append("  No valid returned-loan durations were available.")
        else:
            lines.extend(
                [
                    f"  Loans with valid duration: {len(duration)}",
                    f"  Mean days: {duration.mean():.2f}",
                    f"  Median days: {duration.median():.2f}",
                    f"  Minimum days: {int(duration.min())}",
                    f"  Maximum days: {int(duration.max())}",
                ]
            )

    REPORT_FILE.parent.mkdir(parents=True, exist_ok=True)
    report = "\n".join(lines) + "\n"
    REPORT_FILE.write_text(report, encoding="utf-8")
    print(report)
    print(f"Summary saved to: {REPORT_FILE}")


if __name__ == "__main__":
    main()
