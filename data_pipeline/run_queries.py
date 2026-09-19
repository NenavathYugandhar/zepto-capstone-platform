"""Runs the required SQL queries against zepto_books.db and cross-checks
the JOIN query's result using pandas (pd.read_sql vs. pd.merge, no SQL).

Output is printed to stdout AND written to query_output.md so results are
captured as evidence in the repository.
"""
import sqlite3

import pandas as pd

DB_PATH = "data/zepto_books.db"

QUERIES = {
    "1. SELECT/WHERE — in-stock books priced under £20": """
        SELECT title, price_gbp, in_stock
        FROM books
        WHERE in_stock = 1 AND price_gbp < 20;
    """,
    "2. ORDER BY + LIMIT — 5 most expensive books": """
        SELECT title, price_gbp
        FROM books
        ORDER BY price_gbp DESC
        LIMIT 5;
    """,
    "3. DISTINCT — distinct rating values present": """
        SELECT DISTINCT rating
        FROM books
        ORDER BY rating;
    """,
    "4. BETWEEN — books priced between £20 and £40": """
        SELECT title, price_gbp
        FROM books
        WHERE price_gbp BETWEEN 20 AND 40
        ORDER BY price_gbp;
    """,
    "5. IN — books rated 4 or 5 stars": """
        SELECT title, rating
        FROM books
        WHERE rating IN (4, 5)
        ORDER BY rating DESC;
    """,
    "6. JOIN — top 3 highest-rated books per category": """
        SELECT c.category_name, b.title, b.rating
        FROM books b
        JOIN categories c ON b.category_id = c.category_id
        WHERE b.rating >= 4
        ORDER BY c.category_name, b.rating DESC;
    """,
}


def run_all_queries(db_path: str = DB_PATH) -> dict[str, pd.DataFrame]:
    conn = sqlite3.connect(db_path)
    results = {}
    for label, sql in QUERIES.items():
        results[label] = pd.read_sql(sql, conn)
    conn.close()
    return results


def cross_check_join(db_path: str = DB_PATH) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Reproduces query 6 (the JOIN) two ways: pd.read_sql and pd.merge."""
    conn = sqlite3.connect(db_path)

    sql_result = pd.read_sql(
        """
        SELECT c.category_name, b.title, b.rating
        FROM books b
        JOIN categories c ON b.category_id = c.category_id
        WHERE b.rating >= 4
        ORDER BY c.category_name, b.rating DESC;
        """,
        conn,
    )

    books_df = pd.read_sql("SELECT * FROM books", conn)
    categories_df = pd.read_sql("SELECT * FROM categories", conn)
    conn.close()

    merge_result = (
        books_df.merge(categories_df, on="category_id")
        .query("rating >= 4")[["category_name", "title", "rating"]]
        .sort_values(["category_name", "rating"], ascending=[True, False])
        .reset_index(drop=True)
    )
    sql_result = sql_result.reset_index(drop=True)

    return sql_result, merge_result


if __name__ == "__main__":
    lines = ["# Query Output\n"]

    results = run_all_queries()
    for label, df in results.items():
        print(f"\n--- {label} ---")
        print(df.to_string(index=False))
        lines.append(f"## {label}\n")
        lines.append("```\n" + df.to_string(index=False) + "\n```\n")

    sql_result, merge_result = cross_check_join()
    match = sql_result.equals(merge_result)
    print(f"\n--- pd.read_sql vs pd.merge (JOIN cross-check) ---")
    print("pd.read_sql result:\n", sql_result.to_string(index=False))
    print("\npd.merge result:\n", merge_result.to_string(index=False))
    print(f"\nOutputs match: {match}")

    lines.append("## pd.read_sql vs pd.merge cross-check (JOIN query, no SQL for the merge side)\n")
    lines.append("**pd.read_sql result:**\n\n```\n" + sql_result.to_string(index=False) + "\n```\n")
    lines.append("**pd.merge result:**\n\n```\n" + merge_result.to_string(index=False) + "\n```\n")
    lines.append(f"\n**Outputs match: {match}**\n")

    with open("query_output.md", "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print("\nSaved full output to query_output.md")
