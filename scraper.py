# scraper.py
import time
import pandas as pd
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from db import init_db, upsert_listings

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; CarSenseAI/1.0; +https://example.com)"
}

def parse_listing(div):
    """
    Example parser for a card on a sgCarMart category/search page.
    Adjust SELECTORS after viewing HTML (use browser devtools).
    """
    try:
        a = div.select_one("a.ad-title") or div.select_one("a")
        url = f"https://www.sgcarmart.com{a['href']}" if a and a.get("href","").startswith("/") else a["href"]

        title = (a.get_text(" ", strip=True) if a else "").split()
        # crude splits; refine with regex based on title format
        make = title[0] if title else ""
        model = title[1] if len(title) > 1 else ""

        price_txt = div.get_text(" ", strip=True)
        # naive parse; refine with regex
        price = None
        for token in price_txt.split():
            if token.replace(",", "").replace("$", "").isdigit():
                price = int(token.replace(",", "").replace("$", ""))
                break

        # placeholders; refine with more selectors
        variant = div.get_text(" ", strip=True)
        year = None
        mileage_km = None
        colour = None
        trans = None
        coe_left_years = None

        return {
            "source": "sgcarmart",
            "url": url,
            "make": make,
            "model": model,
            "variant": variant[:120],
            "year": year or 2021,
            "price": price or 0,
            "mileage_km": mileage_km or 50000,
            "colour": colour or "White",
            "reg_date": None,
            "trans": trans or "Auto",
            "coe_left_years": coe_left_years or 7.5,
            "scraped_at": datetime.utcnow().isoformat()
        }
    except Exception:
        return None

def scrape_search_page(url):
    r = requests.get(url, headers=HEADERS, timeout=20)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    cards = soup.select("div.ad-listing") or soup.select("div.search_listings")
    rows = []
    for c in cards:
        row = parse_listing(c)
        if row:
            rows.append(row)
    return pd.DataFrame(rows)

def run_scrape():
    init_db()
    # Example: search UX250h or Ioniq 5 pages you identify.
    targets = [
        # Replace with actual search URLs you want to track
        "https://www.sgcarmart.com/used_cars/listing.php?MOD=ux250h",
        "https://www.sgcarmart.com/used_cars/listing.php?MOD=ioniq%205"
    ]
    all_rows = []
    for url in targets:
        try:
            df = scrape_search_page(url)
            if not df.empty:
                all_rows.append(df)
            time.sleep(2)
        except Exception as e:
            print("Error scraping:", url, e)

    if all_rows:
        final = pd.concat(all_rows, ignore_index=True).drop_duplicates(subset=["url"])
        upsert_listings(final)
        print(f"Scraped & stored {len(final)} rows.")
    else:
        print("No rows scraped.")

if __name__ == "__main__":
    run_scrape()
