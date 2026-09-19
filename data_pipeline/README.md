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
