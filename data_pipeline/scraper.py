"""Scrapes book listings from books.toscrape.com across multiple categories.

Captures, per book: title, price (GBP, as listed), star_rating (as text),
availability (as listed text), and category.
"""
import time
from urllib.parse import urljoin

import pandas as pd
import requests
from bs4 import BeautifulSoup

BASE_URL = "https://books.toscrape.com/"
CATEGORIES = {
    "Travel": "catalogue/category/books/travel_2/index.html",
    "Mystery": "catalogue/category/books/mystery_3/index.html",
    "Historical Fiction": "catalogue/category/books/historical-fiction_4/index.html",
}


def scrape_category(category_name: str, start_url: str) -> list[dict]:
    """Scrapes every page of one category, following the 'next' link until exhausted."""
    books = []
    url = urljoin(BASE_URL, start_url)

    while url:
        response = requests.get(url)
        response.raise_for_status()
        # The site doesn't declare a charset in its HTTP headers, so requests
        # defaults to Latin-1 and mangles the £ symbol (e.g. "Â£45.17").
        # The page is actually UTF-8, so set it explicitly before parsing.
        response.encoding = "utf-8"
        soup = BeautifulSoup(response.text, "html.parser")

        for card in soup.find_all("article", class_="product_pod"):
            title = card.h3.a["title"]
            price = card.find("p", class_="price_color").text
            rating = card.find("p", class_="star-rating")["class"][1]
            availability = card.find("p", class_="instock availability").text.strip()

            books.append(
                {
                    "title": title,
                    "price": price,
                    "star_rating": rating,
                    "availability": availability,
                    "category": category_name,
                }
            )

        next_link = soup.find("li", class_="next")
        url = urljoin(url, next_link.a["href"]) if next_link else None
        time.sleep(0.2)  # be polite to the practice site

    return books


def scrape_all_categories(categories: dict[str, str] = CATEGORIES) -> pd.DataFrame:
    all_books = []
    for name, path in categories.items():
        category_books = scrape_category(name, path)
        print(f"  scraped {len(category_books)} books from category '{name}'")
        all_books.extend(category_books)
    return pd.DataFrame(all_books)


if __name__ == "__main__":
    df = scrape_all_categories()
    print(f"\nTotal books scraped: {len(df)}")
    df.to_csv("data/books_raw.csv", index=False)
    print("Saved to data/books_raw.csv")
