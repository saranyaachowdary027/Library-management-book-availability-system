
import pandas as pd
from pathlib import Path

# Find the project root folder
project_root = Path(__file__).resolve().parent.parent

files = {
    "ORIGINAL DATASET": project_root / "data" / "raw" / "library_datasets.csv",
    "CLEANED DATASET": project_root / "data" / "processed" / "library_datasets_cleaned.csv",
}

for label, file_path in files.items():
    print("\n" + "=" * 60)
    print(label)
    print("=" * 60)

    if not file_path.exists():
        print("File not found:", file_path)
        continue

    df = pd.read_csv(file_path)

    print("File:", file_path.name)
    print("Rows and columns:", df.shape)

    print("\nColumn names:")
    print(df.columns.tolist())

    print("\nFirst 5 rows:")
    print(df.head().to_string(index=False))

    print("\nMissing values per column:")
    print(df.isnull().sum().to_string())

    print("\nDuplicate rows:", df.duplicated().sum())
