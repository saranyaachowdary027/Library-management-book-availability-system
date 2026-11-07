from db import initialize_database, get_connection


def seed_sample_books():
    initialize_database()

    sample_books = [
        ("9780000000001", "Python Programming", "Sample Author", "Technology", 5),
        ("9780000000002", "Database Systems", "Sample Author", "Technology", 3),
        ("9780000000003", "Data Visualization", "Sample Author", "Data Science", 4),
        ("9780000000004", "Machine Learning", "Sample Author", "Artificial Intelligence", 2),
        ("9780000000005", "Software Engineering", "Sample Author", "Technology", 4),
    ]

    with get_connection() as connection:
        connection.executemany(
            """
            INSERT OR IGNORE INTO books
            (isbn, title, author, category, total_copies)
            VALUES (?, ?, ?, ?, ?)
            """,
            sample_books,
        )

    print("Sample books added successfully.")


if __name__ == "__main__":
    seed_sample_books()