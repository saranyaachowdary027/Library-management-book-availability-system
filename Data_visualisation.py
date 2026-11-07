"""Create reproducible charts from the cleaned library dataset."""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parent
DATA_FILE = PROJECT_ROOT / "data" / "processed" / "library_datasets_cleaned.csv"
REPORTS_DIR = PROJECT_ROOT / "reports"


def save_bar_chart(series: pd.Series, title: str, xlabel: str, filename: str) -> None:
    if series.empty:
        return
    ax = series.plot(kind="bar", color="#5266a8")
    ax.set_title(title)
    ax.set_xlabel(xlabel)
    ax.set_ylabel("Number of records")
    plt.xticks(rotation=35, ha="right")
    plt.tight_layout()
    plt.savefig(REPORTS_DIR / filename, dpi=150)
    plt.close()


def main() -> None:
    if not DATA_FILE.is_file():
        raise FileNotFoundError(
            f"Cleaned dataset not found: {DATA_FILE}. Run data_cleaning.py first."
        )

    data = pd.read_csv(DATA_FILE)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    charts_created = 0

    if "book_category" in data.columns:
        counts = data["book_category"].fillna("Unknown").value_counts().head(12)
        save_bar_chart(
            counts,
            "Library records by book category",
            "Book category",
            "book_category.png",
        )
        charts_created += int(not counts.empty)

    if "reservation_status" in data.columns:
        counts = data["reservation_status"].fillna("Unknown").astype(str).value_counts()
        save_bar_chart(
            counts,
            "Reservation status distribution",
            "Reservation status",
            "reservation_status.png",
        )
        charts_created += int(not counts.empty)

    if "overdue_status" in data.columns:
        overdue = pd.to_numeric(data["overdue_status"], errors="coerce")
        labels = overdue.map({0: "Not overdue", 1: "Overdue"}).fillna("Unknown")
        counts = labels.value_counts()
        save_bar_chart(
            counts,
            "Overdue status distribution",
            "Overdue status",
            "overdue_status.png",
        )
        charts_created += int(not counts.empty)

    if {"borrow_date", "return_date"}.issubset(data.columns):
        borrowed = pd.to_datetime(data["borrow_date"], errors="coerce")
        returned = pd.to_datetime(data["return_date"], errors="coerce")
        duration = (returned - borrowed).dt.days.dropna()
        if not duration.empty:
            ax = duration.plot(kind="hist", bins=15, color="#68a39b")
            ax.set_title("Borrowing duration for returned loans")
            ax.set_xlabel("Days")
            ax.set_ylabel("Number of records")
            plt.tight_layout()
            plt.savefig(REPORTS_DIR / "borrowing_duration.png", dpi=150)
            plt.close()
            charts_created += 1

    print(f"Charts created: {charts_created}")
    print(f"Charts saved in: {REPORTS_DIR}")


if __name__ == "__main__":
    main()
