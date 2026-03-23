from __future__ import annotations

import re
from urllib.parse import quote

import requests
from bs4 import BeautifulSoup

from models import TrackResult

STORE_NAME = "Juno Download"
_STORE_URL = "https://www.junodownload.com"
_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml",
    "Accept-Language": "en-US,en;q=0.9",
}


def _parse_price(s: str) -> float | None:
    m = re.search(r"[\d.]+", s)
    return float(m.group()) if m else None


def search(query: str) -> list[TrackResult]:
    try:
        url = f"{_STORE_URL}/search/?q%5Ball%5D%5B%5D={quote(query)}&solrorder=relevancy"
        resp = requests.get(url, headers=_HEADERS, timeout=10)
        if not resp.ok:
            return []

        soup = BeautifulSoup(resp.text, "html.parser")
        results: list[TrackResult] = []

        for el in soup.select(".product-tracklist .product-tracklist-track, .jd-listing-item, .product"):
            title_el = el.select_one(".product-tracklist-track-title a, .juno-title a, .product-title a")
            title = title_el.get_text(strip=True) if title_el else ""
            artist = ", ".join(a.get_text(strip=True) for a in el.select(".product-tracklist-track-artists a, .juno-artist a, .product-artist a"))
            label_el = el.select_one(".product-label a, .juno-label a")
            label = label_el.get_text(strip=True) if label_el else ""
            genre_el = el.select_one(".product-genre a, .juno-genre a")
            genre = genre_el.get_text(strip=True) if genre_el else ""
            price_el = el.select_one(".product-buy .price, .buy-btn-price, .product-price")
            price_text = price_el.get_text(strip=True) if price_el else ""
            link = title_el["href"] if title_el and title_el.get("href") else None
            img_el = el.select_one("img")
            img = (img_el.get("data-src") or img_el.get("src")) if img_el else None

            if title:
                full_url = link if link and link.startswith("http") else f"{_STORE_URL}{link}" if link else f"{_STORE_URL}/search/?q%5Ball%5D%5B%5D={quote(query)}"
                results.append(TrackResult(
                    title=title,
                    artist=artist,
                    label=label,
                    genre=genre,
                    bpm=None,
                    key=None,
                    duration="",
                    price=price_text or "£1.49",
                    price_value=_parse_price(price_text or "£1.49"),
                    currency="GBP",
                    artwork=img,
                    url=full_url,
                    store=STORE_NAME,
                    store_icon="juno",
                    release_date="",
                ))

        return results[:25]
    except Exception as e:
        print(f"Juno Download search error: {e}")
        return []
