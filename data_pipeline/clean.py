"""Cleans raw scraped book data into properly typed columns.

- price -> price_gbp (float)
- star_rating (word) -> rating (int 1-5)
- availability (text) -> in_stock (bool)
- price_gbp -> price_inr (fixed-rate conversion)
"""
import pandas as pd

GBP_TO_INR_RATE = 105.50  # fixed, project-defined constant (not a live/market rate)

RATING_WORDS = {"One": 1, "Two": 2, "Three": 3, "Four": 4, "Five": 5}


def parse_price(price_text: str) -> float | None:
    try:
        return float(price_text.replace("£", "").strip())
    except (ValueError, AttributeError):
        return None


def parse_rating(rating_word: str) -> int | None:
    return RATING_WORDS.get(rating_word)


def parse_availability(availability_text: str) -> bool | None:
    text = availability_text.strip().lower()
    if "in stock" in text:
        return True
    if "out of stock" in text:
        return False
    return None


def clean_books(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["price_gbp"] = df["price"].apply(parse_price)
    df["rating"] = df["star_rating"].apply(parse_rating)
    df["in_stock"] = df["availability"].apply(parse_availability)

    before = len(df)
    # Rows where a field failed to parse are dropped rather than imputed:
    # these are categorical/text fields (not a continuous numeric quantity
    # like price), so a "median" or "most common" fill-in would fabricate
    # a rating/stock-status that was never actually scraped, which is worse
    # than simply excluding the row. Median-imputation is reserved below
    # for price_gbp specifically, since price is numeric and a missing
    # price genuinely has a reasonable typical-value estimate.
    unparsed = df["rating"].isna() | df["in_stock"].isna()
    if unparsed.any():
        print(f"Dropping {unparsed.sum()} row(s) with unparseable rating/availability")
        df = df[~unparsed]

    missing_price = df["price_gbp"].isna()
    if missing_price.any():
        median_price = df["price_gbp"].median()
        print(f"Imputing {missing_price.sum()} missing price(s) with median {median_price:.2f}")
        df.loc[missing_price, "price_gbp"] = median_price

    dropped = before - len(df)
    print(f"Cleaning complete: {before} -> {len(df)} rows ({dropped} dropped)")

    df["rating"] = df["rating"].astype(int)
    df["in_stock"] = df["in_stock"].astype(bool)
    df["price_inr"] = (df["price_gbp"] * GBP_TO_INR_RATE).round(2)

    return df[["title", "price_gbp", "price_inr", "rating", "in_stock", "category"]]


if __name__ == "__main__":
    raw = pd.read_csv("data/books_raw.csv")
    cleaned = clean_books(raw)
    cleaned.to_csv("data/books_clean.csv", index=False, encoding="utf-8")
    print(cleaned.head())
    print(f"\nSaved {len(cleaned)} cleaned rows to data/books_clean.csv")
