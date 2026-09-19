# Data Pipeline

Scrapes book listings from [books.toscrape.com](https://books.toscrape.com), cleans them into
typed columns, converts price to INR at a fixed rate, and loads everything into a normalized
SQLite database that is then queried with both raw SQL and pandas.

## Setup

```
pip install -r requirements.txt
```

## Run end to end

```
python scraper.py         # -> data/books_raw.csv
python clean.py           # -> data/books_clean.csv
python build_database.py  # -> data/zepto_books.db
python run_queries.py     # -> prints + query_output.md
```

## Scope and design decisions

- **Scope chosen:** 3 categories (Travel, Mystery, Historical Fiction), all pages per category,
  followed via the "next" pagination link — 69 books total (≥ 60 required).
- **Currency conversion:** fixed rate of **1 GBP = 105.50 INR**, a project-defined constant with
  no date reference (not a live/market rate), per the assignment spec.
- **Encoding fix:** the site doesn't declare a charset in its HTTP headers, so `requests`
  defaults to Latin-1 and mangles the £ symbol (e.g. `Â£45.17`). `scraper.py` sets
  `response.encoding = "utf-8"` explicitly before parsing to fix this.
- **Missing/unparseable data handling:**
  - `rating` and `in_stock` are parsed from short controlled-vocabulary text (`"Three"`,
    `"In stock"`). If either fails to parse, the **row is dropped** — these are categorical
    fields, so there's no meaningful "average" value to impute; fabricating a rating or
    stock-status would be worse than excluding the row.
  - `price_gbp` is numeric, so a missing/unparseable price is **imputed with the column
    median** instead of dropping the row, since price has a reasonable typical-value estimate
    and dropping a book just because its price string was malformed would lose otherwise-good
    data.
  - On the actual scraped data, 0 rows required either treatment — the site's markup was clean.
- **Schema:** two tables, `categories(category_id PK, category_name)` and
  `books(book_id PK, title, price_gbp, price_inr, rating, in_stock, category_id FK)`.
- **Cross-check:** `run_queries.py` reproduces the JOIN query's result via `pd.merge` on
  in-memory DataFrames (no SQL) and confirms it matches the `pd.read_sql` result exactly.

## Code Walkthrough: how `scraper.py` actually works

### The big picture

```
For each of 3 categories (Travel, Mystery, Historical Fiction):
    Start at page 1 of that category
    While there's a page to read:
        Grab all 20 books on this page
        Is there a "next" button?
            Yes -> go to that page, repeat
            No  -> stop, this category is done
    Add all books from this category to the big pile
Combine all 3 piles into one table -> save as books_raw.csv
```

### Part 1 — one category, one page at a time

```python
def scrape_category(category_name: str, start_url: str) -> list[dict]:
    books = []
    url = urljoin(BASE_URL, start_url)

    while url:
        response = requests.get(url)
        ...
```

The `while url:` loop keeps going **as long as `url` is not `None`**:

```
url = ".../travel_2/index.html"   (page 1, 20 books)
        |
        v  scrape this page, then look for a "next" link
url = ".../travel_2/page-2.html"   (page 2, more books)
        |
        v  scrape this page too, look for "next" again
url = None    <-- no "next" link found (this is the last page)
        |
        v  while url: sees None ("falsy") -> loop STOPS
```

This is driven by:
```python
next_link = soup.find("li", class_="next")
url = urljoin(url, next_link.a["href"]) if next_link else None
```
Plain English: *"Look for a `<li class='next'>` tag. Found one? Follow its link — that's the next page. Not found? Set `url` to `None`, which ends the loop next check."*

### Part 2 — grabbing all ~20 books on one page

```python
for card in soup.find_all("article", class_="product_pod"):
    title = card.h3.a["title"]
    price = card.find("p", class_="price_color").text
    rating = card.find("p", class_="star-rating")["class"][1]
    availability = card.find("p", class_="instock availability").text.strip()
    books.append({...})
```

```
Page HTML (one big blob of text)
        |
        v  find_all("article", class_="product_pod")
[card_1, card_2, card_3, ... card_20]     <-- a list of book "chunks"
        |
        v  for card in that list:
card_1 -> extract 4 fields -> save as one dict -> add to `books`
card_2 -> same thing
...
```

What each extraction line actually does, with a real example:
```python
title = card.h3.a["title"]
# card.h3.a is the <a> link inside the <h3> heading; ["title"] reads its title attribute
# Result: "It's Only the Himalayas"

price = card.find("p", class_="price_color").text
# Result: "£45.17"  (still text — clean.py converts this to a real number later)

rating = card.find("p", class_="star-rating")["class"][1]
# The tag looks like <p class="star-rating Two">
# ["class"] gives ['star-rating', 'Two'] — a list of 2 words; [1] takes the second one
# Result: "Two"

availability = card.find("p", class_="instock availability").text.strip()
# .text grabs "  \n  In stock  \n  " (messy spacing); .strip() cleans it up
# Result: "In stock"
```

Each book becomes one dictionary:
```python
{"title": "It's Only the Himalayas", "price": "£45.17", "star_rating": "Two",
 "availability": "In stock", "category": "Travel"}
```

### Part 3 — all 3 categories combined, then saved

```python
def scrape_all_categories(categories: dict[str, str] = CATEGORIES) -> pd.DataFrame:
    all_books = []
    for name, path in categories.items():
        category_books = scrape_category(name, path)   # everything from Parts 1-2, for ONE category
        all_books.extend(category_books)                 # dump into the big pile
    return pd.DataFrame(all_books)                        # turn the pile into a table
```

```
CATEGORIES = {"Travel": ..., "Mystery": ..., "Historical Fiction": ...}
        |
        v  loop 3 times
scrape_category("Travel", ...)             -> 11 books
scrape_category("Mystery", ...)            -> 32 books
scrape_category("Historical Fiction", ...) -> 26 books
        |
        v  all_books.extend(...) each time -> one combined list of 69 dicts
        |
        v  pd.DataFrame(all_books)
one table, 69 rows, 5 columns (title, price, star_rating, availability, category)
```

Finally:
```python
if __name__ == "__main__":
    df = scrape_all_categories()
    df.to_csv("data/books_raw.csv", index=False)
```
The `if __name__ == "__main__":` guard means: *"only run this when executing `python scraper.py` directly — not when another file imports functions from this one."*

## Code Walkthrough: `clean.py` (fully annotated)

```python
"""Cleans raw scraped book data into properly typed columns."""
import pandas as pd

GBP_TO_INR_RATE = 105.50
# ^ A constant, in ALL_CAPS by convention (signals "this never changes
#   while the program runs"). Fixed per the assignment — not a live rate.

RATING_WORDS = {"One": 1, "Two": 2, "Three": 3, "Four": 4, "Five": 5}
# ^ A lookup table: given the text word, get the number. This is how we
#   turn scraper.py's "Two" into an actual int(2) we can do math on.


def parse_price(price_text: str) -> float | None:
    try:
        return float(price_text.replace("£", "").strip())
        # ^ "£45.17" -> remove "£" -> "45.17" -> strip whitespace -> float(45.17)
    except (ValueError, AttributeError):
        # ^ If the text is something unexpected (e.g. empty, or not a number
        #   at all), float() would crash the whole script. Catching the
        #   error here means ONE bad row doesn't kill the entire pipeline.
        return None
        # ^ Returning None signals "couldn't parse this" — clean_books()
        #   below checks for this and imputes the median in that case.


def parse_rating(rating_word: str) -> int | None:
    return RATING_WORDS.get(rating_word)
    # ^ dict.get() returns the matching number, or None if the word isn't
    #   found in the lookup table at all (e.g. unexpected text) — safer
    #   than RATING_WORDS[rating_word], which would crash on a miss.


def parse_availability(availability_text: str) -> bool | None:
    text = availability_text.strip().lower()
    if "in stock" in text:
        return True
    if "out of stock" in text:
        return False
    return None
    # ^ Checks for the two known phrases; anything else (unexpected text)
    #   returns None rather than guessing.


def clean_books(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    # ^ Work on a COPY, not the original DataFrame — avoids accidentally
    #   modifying the caller's data (a common source of confusing bugs).

    df["price_gbp"] = df["price"].apply(parse_price)
    df["rating"] = df["star_rating"].apply(parse_rating)
    df["in_stock"] = df["availability"].apply(parse_availability)
    # ^ .apply(function) runs `function` on EVERY row's value in that column,
    #   one at a time, and creates a new column from the results. This is
    #   the pandas equivalent of writing a for-loop over every row.

    before = len(df)
    unparsed = df["rating"].isna() | df["in_stock"].isna()
    # ^ .isna() gives True/False per row (True = this value is None/missing).
    #   The `|` is "OR" — True if EITHER rating OR in_stock failed to parse.

    if unparsed.any():
        # ^ .any() checks: is there at least one True in that True/False series?
        print(f"Dropping {unparsed.sum()} row(s) with unparseable rating/availability")
        df = df[~unparsed]
        # ^ `~` flips True/False (NOT). df[~unparsed] keeps only the rows
        #   where unparsed was False — i.e. drops the bad ones.

    missing_price = df["price_gbp"].isna()
    if missing_price.any():
        median_price = df["price_gbp"].median()
        print(f"Imputing {missing_price.sum()} missing price(s) with median {median_price:.2f}")
        df.loc[missing_price, "price_gbp"] = median_price
        # ^ df.loc[condition, "column"] = value means "for only the rows
        #   matching this condition, set this column to this value" —
        #   fills in JUST the missing prices, leaves everything else untouched.

    dropped = before - len(df)
    print(f"Cleaning complete: {before} -> {len(df)} rows ({dropped} dropped)")

    df["rating"] = df["rating"].astype(int)
    df["in_stock"] = df["in_stock"].astype(bool)
    # ^ .astype() forces the column's data type. Needed because after
    #   dropping the NaN rows above, pandas still stores the column as a
    #   generic "object" or float type — this locks it in as real int/bool.

    df["price_inr"] = (df["price_gbp"] * GBP_TO_INR_RATE).round(2)
    # ^ Simple multiplication, applied to the WHOLE column at once (no loop
    #   needed) — this is "vectorized" pandas math. .round(2) keeps 2 decimals.

    return df[["title", "price_gbp", "price_inr", "rating", "in_stock", "category"]]
    # ^ Selects and reorders just these 6 columns for the final output —
    #   drops the original messy "price"/"star_rating"/"availability" text
    #   columns since we don't need them anymore.


if __name__ == "__main__":
    raw = pd.read_csv("data/books_raw.csv")
    cleaned = clean_books(raw)
    cleaned.to_csv("data/books_clean.csv", index=False, encoding="utf-8")
    print(cleaned.head())
    print(f"\nSaved {len(cleaned)} cleaned rows to data/books_clean.csv")
```

## Code Walkthrough: `build_database.py` (fully annotated)

```python
"""Builds a normalized SQLite database from the cleaned book data."""
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
# ^ Two tables. `categories` holds each unique category name ONCE.
#   `books` holds one row per book, and instead of repeating the category
#   NAME on every single book row, it stores just a category_id NUMBER
#   that POINTS BACK to the categories table (the "FOREIGN KEY"). This is
#   what "normalized" means — no duplicated text data across rows.


def build_database(csv_path: str = "data/books_clean.csv", db_path: str = DB_PATH) -> None:
    df = pd.read_csv(csv_path)

    conn = sqlite3.connect(db_path)
    # ^ Opens (or creates, if it doesn't exist yet) the .db file on disk.
    cursor = conn.cursor()
    # ^ The "cursor" is what you use to actually run SQL commands.

    cursor.executescript("DROP TABLE IF EXISTS books; DROP TABLE IF EXISTS categories;")
    cursor.executescript(SCHEMA)
    # ^ Wipes any old tables first, then recreates them fresh — makes this
    #   script safe to re-run from scratch any time, rather than erroring
    #   out on "table already exists" or silently duplicating data.

    category_ids = {}
    # ^ A lookup: category NAME -> the auto-generated NUMBER SQLite gave it.
    #   We need this because books.csv only has the category NAME as text,
    #   but the books table needs the category_id NUMBER to link to it.

    for category_name in df["category"].unique():
        # ^ .unique() gives each distinct category name exactly once
        #   (e.g. "Travel", "Mystery", "Historical Fiction" — not 69 times).
        cursor.execute(
            "INSERT INTO categories (category_name) VALUES (?)", (category_name,)
        )
        # ^ The "?" is a placeholder — sqlite3 safely inserts the actual
        #   value in place of it. (Never build SQL by string-concatenating
        #   values directly — that's how SQL-injection bugs happen.)
        category_ids[category_name] = cursor.lastrowid
        # ^ .lastrowid gives the auto-generated category_id SQLite just
        #   assigned to the row we just inserted. We remember it here.

    book_rows = [
        (
            row.title,
            row.price_gbp,
            row.price_inr,
            int(row.rating),
            int(bool(row.in_stock)),
            category_ids[row.category],
            # ^ Look up THIS book's category name in our dict from above,
            #   to get the matching category_id number to store instead.
        )
        for row in df.itertuples()
        # ^ .itertuples() walks through the DataFrame one row at a time,
        #   letting us access each column as row.column_name.
    ]
    cursor.executemany(
        """INSERT INTO books (title, price_gbp, price_inr, rating, in_stock, category_id)
           VALUES (?, ?, ?, ?, ?, ?)""",
        book_rows,
    )
    # ^ .executemany() runs the same INSERT statement once per tuple in
    #   book_rows — much faster than calling .execute() 69 separate times.

    conn.commit()
    # ^ Without this, none of the inserts would actually be saved to disk —
    #   SQLite (like most databases) requires an explicit "commit" to
    #   make changes permanent.
    print(f"Inserted {len(category_ids)} categories and {len(book_rows)} books into {db_path}")
    conn.close()


if __name__ == "__main__":
    build_database()
```

## Code Walkthrough: `run_queries.py` (fully annotated)

```python
"""Runs the required SQL queries and cross-checks the JOIN with pandas."""
import sqlite3
import pandas as pd

DB_PATH = "data/zepto_books.db"

QUERIES = {
    "1. SELECT/WHERE — in-stock books priced under £20": """
        SELECT title, price_gbp, in_stock
        FROM books
        WHERE in_stock = 1 AND price_gbp < 20;
    """,
    # ^ ... 5 more queries follow this same {label: sql_string} pattern,
    #   covering ORDER BY/LIMIT, DISTINCT, BETWEEN, IN, and a JOIN.
    #   Storing them as a dict means run_all_queries() below can loop
    #   over all of them generically instead of repeating code 6 times.
}


def run_all_queries(db_path: str = DB_PATH) -> dict[str, pd.DataFrame]:
    conn = sqlite3.connect(db_path)
    results = {}
    for label, sql in QUERIES.items():
        results[label] = pd.read_sql(sql, conn)
        # ^ pd.read_sql runs the SQL AND returns the result directly as a
        #   DataFrame — no separate cursor.execute() + fetchall() needed.
    conn.close()
    return results


def cross_check_join(db_path: str = DB_PATH) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Reproduces the JOIN query two ways: pd.read_sql and pd.merge."""
    conn = sqlite3.connect(db_path)

    sql_result = pd.read_sql(
        """SELECT c.category_name, b.title, b.rating
           FROM books b JOIN categories c ON b.category_id = c.category_id
           WHERE b.rating >= 4 ORDER BY c.category_name, b.rating DESC;""",
        conn,
    )
    # ^ The SQL-based approach: the database itself does the joining.

    books_df = pd.read_sql("SELECT * FROM books", conn)
    categories_df = pd.read_sql("SELECT * FROM categories", conn)
    conn.close()

    merge_result = (
        books_df.merge(categories_df, on="category_id")
        # ^ pandas does the SAME join the database did, but in memory —
        #   matches rows between the two tables wherever category_id agrees.
        .query("rating >= 4")[["category_name", "title", "rating"]]
        .sort_values(["category_name", "rating"], ascending=[True, False])
        .reset_index(drop=True)
        # ^ .reset_index(drop=True) renumbers rows 0,1,2,... after sorting —
        #   needed so the two results can be compared row-for-row below.
    )
    sql_result = sql_result.reset_index(drop=True)

    return sql_result, merge_result


if __name__ == "__main__":
    results = run_all_queries()
    for label, df in results.items():
        print(f"\n--- {label} ---")
        print(df.to_string(index=False))

    sql_result, merge_result = cross_check_join()
    match = sql_result.equals(merge_result)
    # ^ .equals() checks the two DataFrames are IDENTICAL — same values,
    #   same order, same types. This is the actual proof the assignment
    #   asks for: "SQL and pandas agree."
    print(f"\nOutputs match: {match}")
```
