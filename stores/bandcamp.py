from __future__ import annotations

import re
from urllib.parse import quote

import requests
from bs4 import BeautifulSoup

from models import TrackResult

STORE_NAME = "Bandcamp"
_STORE_URL = "https://bandcamp.com"
_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml",
    "Accept-Language": "en-US,en;q=0.9",
}


def _parse_price(s: str | None) -> float | None:
    if not s:
        return None
    m = re.search(r"[\d.]+", s)
    return float(m.group()) if m else None


def search(query: str) -> list[TrackResult]:
    try:
        url = f"{_STORE_URL}/search?q={quote(query)}&item_type=t"
        resp = requests.get(url, headers=_HEADERS, timeout=10)
        if not resp.ok:
            return []

        soup = BeautifulSoup(resp.text, "html.parser")
        results: list[TrackResult] = []

        for el in soup.select(".searchresult.track, .result-items .searchresult"):
            heading = el.select_one(".heading a")
            title = heading.get_text(strip=True) if heading else ""
            link = heading["href"] if heading and heading.get("href") else None
            subhead = el.select_one(".subhead")
            subhead_text = subhead.get_text(strip=True) if subhead else ""
            img_el = el.select_one("img.art, .art img")
            img = img_el.get("src") if img_el else None

            artist = ""
            album = ""
            by_match = re.search(r"by\s+(.+)", subhead_text, re.IGNORECASE)
            from_match = re.search(r"from\s+(.+?)(?:\s+by\s+|$)", subhead_text, re.IGNORECASE)
            if by_match:
                artist = by_match.group(1).strip()
            if from_match:
                album = from_match.group(1).strip()

            genre_el = el.select_one(".genre")
            genre = genre_el.get_text(strip=True).replace("genre:", "").strip() if genre_el else ""
            price_el = el.select_one(".price, .buy-now")
            price_text = price_el.get_text(strip=True) if price_el else ""

            if title:
                results.append(TrackResult(
                    title=title,
                    artist=artist,
                    label=album,
                    genre=genre,
                    bpm=None,
                    key=None,
                    duration="",
                    price=price_text or "Name Your Price",
                    price_value=_parse_price(price_text),
                    currency="USD",
                    artwork=img,
                    url=link or f"{_STORE_URL}/search?q={quote(query)}&item_type=t",
                    store=STORE_NAME,
                    store_icon="bandcamp",
                    release_date="",
                ))

        return results[:25]
    except Exception as e:
        print(f"Bandcamp search error: {e}")
        return []
