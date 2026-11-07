"""Clean the raw library borrowing dataset without changing the source file."""

from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parent
RAW_FILE = PROJECT_ROOT / "data" / "raw" / "library_datasets.csv"
CLEAN_FILE = PROJECT_ROOT / "data" / "processed" / "library_datasets_cleaned.csv"

REQUIRED_COLUMNS = {
    "user_id",
    "book_id",
    "borrow_date",
    "return_date",
    "reservation_status",
    "overdue_status",
    "user_role",
    "book_category",
}
DATE_COLUMNS = ("borrow_date", "return_date")
BOOLEAN_VALUES = {
    "true": True,
    "false": False,
    "yes": True,
    "no": False,
    "1": True,
    "0": False,
}


def clean_dataset() -> pd.DataFrame:
    """Read, normalize, and save the cleaned CSV; return the cleaned data."""
    if not RAW_FILE.is_file():
        raise FileNotFoundError(f"Raw dataset not found: {RAW_FILE}")

    data = pd.read_csv(RAW_FILE)
    data.columns = (
        data.columns.astype(str)
        .str.strip()
        .str.lower()
        .str.replace(r"\s+", "_", regex=True)
    )

    missing_columns = REQUIRED_COLUMNS - set(data.columns)
    if missing_columns:
        names = ", ".join(sorted(missing_columns))
        raise ValueError(f"The raw CSV is missing required columns: {names}")

    # Trim text and treat empty cells as missing. A blank return_date can mean
    # the loan is still open, so rows with missing values are retained.
    for column in data.select_dtypes(include=["object", "string"]).columns:
        data[column] = data[column].map(
            lambda value: value.strip() if isinstance(value, str) else value
        )
        data[column] = data[column].replace("", pd.NA)

    original_rows = len(data)
    duplicate_rows = int(data.duplicated().sum())
    data = data.drop_duplicates().copy()

    # Standardize valid dates. If a column contains an unparseable nonblank
    # value, retain that column as text rather than silently erasing the value.
    for column in DATE_COLUMNS:
        original = data[column].astype("string").str.strip()
        parsed = pd.to_datetime(original, errors="coerce")
        invalid = original.notna() & parsed.isna()
        if invalid.any():
            print(
                f"Warning: kept {int(invalid.sum())} unrecognized values in {column}."
            )
            data[column] = original
        else:
            data[column] = parsed.dt.strftime("%Y-%m-%d")

    # Convert reservation flags only when every nonblank value is recognized.
    reservation = data["reservation_status"].astype("string").str.strip().str.lower()
    mapped_reservation = reservation.map(BOOLEAN_VALUES)
    unknown_reservation = reservation.notna() & mapped_reservation.isna()
    if unknown_reservation.any():
        print("Warning: reservation_status contains values outside true/false; kept as text.")
        data["reservation_status"] = reservation
    else:
        data["reservation_status"] = mapped_reservation.astype("boolean")

    # Keep overdue_status numeric when possible, preserving missing/invalid
    # entries as missing values for review instead of treating them as zero.
    overdue = pd.to_numeric(data["overdue_status"], errors="coerce")
    nonblank_overdue = data["overdue_status"].notna()
    invalid_overdue = nonblank_overdue & overdue.isna()
    if invalid_overdue.any():
        print(
            f"Warning: {int(invalid_overdue.sum())} overdue_status values are not numeric."
        )
    data["overdue_status"] = overdue.astype("Int64")

    CLEAN_FILE.parent.mkdir(parents=True, exist_ok=True)
    data.to_csv(CLEAN_FILE, index=False, na_rep="")

    print(f"Input rows: {original_rows}")
    print(f"Exact duplicate rows removed: {duplicate_rows}")
    print(f"Output rows: {len(data)}")
    print("Missing values by column:")
    print(data.isna().sum().to_string())
    print(f"Cleaned dataset saved to: {CLEAN_FILE}")
    return data


if __name__ == "__main__":
    clean_dataset()
