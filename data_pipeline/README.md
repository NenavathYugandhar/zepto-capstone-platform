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
