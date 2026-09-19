"""Builds a normalized SQLite database from the cleaned book data.

Schema:
    categories(category_id INTEGER PRIMARY KEY, category_name TEXT UNIQUE)
    books(book_id INTEGER PRIMARY KEY, title TEXT, price_gbp REAL,
          price_inr REAL, rating INTEGER, in_stock INTEGER,
          category_id INTEGER REFERENCES categories(category_id))
"""
import sqlite3

import pandas as pd

DB_PATH = "data/zepto_books.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS categories (
    category_id INTEGER PRIMARY KEY AUTOINCREMENT,
    category_name TEXT UNIQUE NOT NULL
);

CREATE TABLE IF NOT EXISTS books (
    book_id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    price_gbp REAL NOT NULL,
    price_inr REAL NOT NULL,
    rating INTEGER NOT NULL,
    in_stock INTEGER NOT NULL,
    category_id INTEGER NOT NULL,
    FOREIGN KEY (category_id) REFERENCES categories(category_id)
);
"""


def build_database(csv_path: str = "data/books_clean.csv", db_path: str = DB_PATH) -> None:
    df = pd.read_csv(csv_path)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.executescript("DROP TABLE IF EXISTS books; DROP TABLE IF EXISTS categories;")
    cursor.executescript(SCHEMA)

    category_ids = {}
    for category_name in df["category"].unique():
        cursor.execute(
            "INSERT INTO categories (category_name) VALUES (?)", (category_name,)
        )
        category_ids[category_name] = cursor.lastrowid

    book_rows = [
        (
            row.title,
            row.price_gbp,
            row.price_inr,
            int(row.rating),
            int(bool(row.in_stock)),
            category_ids[row.category],
        )
        for row in df.itertuples()
    ]
    cursor.executemany(
        """INSERT INTO books (title, price_gbp, price_inr, rating, in_stock, category_id)
           VALUES (?, ?, ?, ?, ?, ?)""",
        book_rows,
    )

    conn.commit()
    print(f"Inserted {len(category_ids)} categories and {len(book_rows)} books into {db_path}")
    conn.close()


if __name__ == "__main__":
    build_database()
