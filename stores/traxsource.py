from __future__ import annotations

import re
from urllib.parse import quote

import requests
from bs4 import BeautifulSoup

from models import TrackResult

STORE_NAME = "Traxsource"
_STORE_URL = "https://www.traxsource.com"
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
        url = f"{_STORE_URL}/search?term={quote(query)}"
        resp = requests.get(url, headers=_HEADERS, timeout=10)
        if not resp.ok:
            return []

        soup = BeautifulSoup(resp.text, "html.parser")
        results: list[TrackResult] = []

        for el in soup.select(".trk-row, .search-trk-row"):
            title_el = el.select_one(".title a, .trk-name a")
            title = title_el.get_text(strip=True) if title_el else ""
            artist = ", ".join(a.get_text(strip=True) for a in el.select(".artists a, .trk-artists a"))
            label_el = el.select_one(".label a, .trk-label a")
            label = label_el.get_text(strip=True) if label_el else ""
            genre_el = el.select_one(".genre a, .trk-genre a")
            genre = genre_el.get_text(strip=True) if genre_el else ""
            price_el = el.select_one(".add-cart .price, .buy-btn, .trk-price")
            price_text = price_el.get_text(strip=True) if price_el else ""
            link = title_el["href"] if title_el and title_el.get("href") else None
            img_el = el.select_one("img.lazy, img.trk-art")
            img = (img_el.get("data-src") or img_el.get("src")) if img_el else None
            if not img:
                first_img = el.select_one("img")
                img = first_img.get("src") if first_img else None

            if title:
                bpm_el = el.select_one(".bpm, .trk-bpm")
                key_el = el.select_one(".key, .trk-key")
                dur_el = el.select_one(".duration, .trk-duration")

                full_url = link if link and link.startswith("http") else f"{_STORE_URL}{link}" if link else f"{_STORE_URL}/search?term={quote(query)}"
                results.append(TrackResult(
                    title=title,
                    artist=artist,
                    label=label,
                    genre=genre,
                    bpm=bpm_el.get_text(strip=True) if bpm_el else None,
                    key=key_el.get_text(strip=True) if key_el else None,
                    duration=dur_el.get_text(strip=True) if dur_el else "",
                    price=price_text or "$1.49",
                    price_value=_parse_price(price_text or "$1.49"),
                    currency="USD",
                    artwork=img,
                    url=full_url,
                    store=STORE_NAME,
                    store_icon="traxsource",
                    release_date="",
                ))

        return results[:25]
    except Exception as e:
        print(f"Traxsource search error: {e}")
        return []
