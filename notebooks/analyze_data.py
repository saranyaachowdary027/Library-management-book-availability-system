import pandas as pd
from pathlib import Path

# Locate the project and cleaned dataset
project_root = Path(__file__).resolve().parent.parent
file_path = project_root / "data" / "processed" / "library_datasets_cleaned.csv"

df = pd.read_csv(file_path)

print("=" * 50)
print("LIBRARY DATA ANALYSIS")
print("=" * 50)

# 1. Dataset size
print("\n1. Dataset size:")
print("Rows:", df.shape[0])
print("Columns:", df.shape[1])

# 2. Column names and data types
print("\n2. Column names:")
print(df.columns.tolist())

print("\n3. Data types:")
print(df.dtypes.to_string())

# 4. Numerical summary
print("\n4. Numerical summary:")
print(df.describe(include="all").to_string())

# 5. Borrowing and reservation analysis
for column in ["reservation_status", "overdue_status",
               "user_role", "book_category"]:
    if column in df.columns:
        print(f"\n5. Distribution of {column}:")
        print(df[column].value_counts(dropna=False).to_string())

# 6. Borrowing duration analysis
if "borrow_duration_days" in df.columns:
    print("\n6. Borrowing duration statistics:")
    print(df["borrow_duration_days"].describe().to_string())

print("\nAnalysis completed.")