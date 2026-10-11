
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path

# Locate the project and cleaned dataset
project_root = Path(__file__).resolve().parent.parent
file_path = project_root / "data" / "processed" / "library_datasets_cleaned.csv"

df = pd.read_csv(file_path)

# 1. Borrowing status distribution
if "reservation_status" in df.columns:
    df["reservation_status"].value_counts().plot(kind="bar")
    plt.title("Library Reservation Status")
    plt.xlabel("Reservation Status")
    plt.ylabel("Number of Records")
    plt.tight_layout()
    plt.savefig(project_root / "reports" / "reservation_status.png")
    plt.show()

# 2. Book category distribution
if "book_category" in df.columns:
    df["book_category"].value_counts().plot(kind="bar")
    plt.title("Library Book Category Distribution")
    plt.xlabel("Book Category")
    plt.ylabel("Number of Records")
    plt.tight_layout()
    plt.savefig(project_root / "reports" / "book_category.png")
    plt.show()

# 3. Borrowing duration distribution
if "borrow_duration_days" in df.columns:
    df["borrow_duration_days"].dropna().plot(kind="hist", bins=10)
    plt.title("Borrowing Duration Distribution")
    plt.xlabel("Borrowing Duration (Days)")
    plt.ylabel("Frequency")
    plt.tight_layout()
    plt.savefig(project_root / "reports" / "borrowing_duration.png")
    plt.show()
    
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path

# Locate the project and cleaned dataset
project_root = Path(__file__).resolve().parent.parent
file_path = project_root / "data" / "processed" / "library_datasets_cleaned.csv"

df = pd.read_csv(file_path)

# 1. Borrowing status distribution
if "reservation_status" in df.columns:
    df["reservation_status"].value_counts().plot(kind="bar")
    plt.title("Library Reservation Status")
    plt.xlabel("Reservation Status")
    plt.ylabel("Number of Records")
    plt.tight_layout()
    plt.savefig(project_root / "reports" / "reservation_status.png")
    plt.show()

# 2. Book category distribution
if "book_category" in df.columns:
    df["book_category"].value_counts().plot(kind="bar")
    plt.title("Library Book Category Distribution")
    plt.xlabel("Book Category")
    plt.ylabel("Number of Records")
    plt.tight_layout()
    plt.savefig(project_root / "reports" / "book_category.png")
    plt.show()

# 3. Borrowing duration distribution
if "borrow_duration_days" in df.columns:
    df["borrow_duration_days"].dropna().plot(kind="hist", bins=10)
    plt.title("Borrowing Duration Distribution")
    plt.xlabel("Borrowing Duration (Days)")
    plt.ylabel("Frequency")
    plt.tight_layout()
    plt.savefig(project_root / "reports" / "borrowing_duration.png")

    plt.show()
    # 4. Book availability / reservation status
df["reservation_status"].value_counts().plot(kind="bar")
plt.title("Book Availability and Reservation Status")
plt.xlabel("Reservation Status")
plt.ylabel("Number of Records")
plt.tight_layout()
plt.savefig(project_root / "reports" / "book_availability.png")
plt.show()

# 5. Most frequently recorded books
df["book_id"].value_counts().head(10).sort_values().plot(kind="barh")
plt.title("Top 10 Most Frequently Recorded Books")
plt.xlabel("Number of Records")
plt.ylabel("Book ID")
plt.tight_layout()
plt.savefig(project_root / "reports" / "popular_books.png")
plt.show()
print("Visualization completed.")
print("Charts saved in the reports folder.")
