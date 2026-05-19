from __future__ import annotations

import re
from urllib.parse import quote

import requests
from bs4 import BeautifulSoup

from models import TrackResult

STORE_NAME = "Amazon Music"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "de-DE,de;q=0.9,en;q=0.8",
}


def _parse_price(text: str) -> tuple[str, float | None]:
    if not text:
        return "N/A", None
    m = re.search(r"(\d+)[,.](\d{2})", text)
    if m:
        value = float(f"{m.group(1)}.{m.group(2)}")
        return f"{value:.2f} EUR", value
    return text.strip(), None


def search(query: str) -> list[TrackResult]:
    try:
        url = f"https://www.amazon.de/s?k={quote(query)}&i=digital-music"
        resp = requests.get(url, headers=HEADERS, timeout=10)
        if not resp.ok:
            return []

        soup = BeautifulSoup(resp.text, "html.parser")
        results: list[TrackResult] = []

        items = soup.select('[data-component-type="s-search-result"]')

        for item in items[:25]:
            # Title
            title_el = item.select_one("h2 a span")
            if not title_el:
                continue
            title = title_el.get_text(strip=True)

            # URL
            link_el = item.select_one("h2 a")
            href = link_el.get("href", "") if link_el else ""
            track_url = f"https://www.amazon.de{href}" if href and not href.startswith("http") else href

            # Artist - often in a second line below the title
            artist = ""
            artist_el = item.select_one(".a-row .a-size-base:not(.a-color-price)")
            if artist_el:
                artist = artist_el.get_text(strip=True)
            if not artist:
                # Try alternative selectors
                for el in item.select(".a-size-base"):
                    text = el.get_text(strip=True)
                    if text and text != title and "EUR" not in text and "von" not in text.lower():
                        artist = text
                        break
                    if text and "von " in text.lower():
                        artist = text.replace("von ", "").strip()
                        break

            # Price
            price_el = item.select_one(".a-price .a-offscreen")
            if not price_el:
                price_el = item.select_one(".a-color-price")
            price_text = price_el.get_text(strip=True) if price_el else ""
            price, price_value = _parse_price(price_text)

            # Artwork
            artwork = None
            img_el = item.select_one("img.s-image")
            if img_el:
                artwork = img_el.get("src")

            results.append(TrackResult(
                title=title,
                artist=artist,
                label="",
                genre="",
                bpm=None,
                key=None,
                duration="",
                price=price,
                price_value=price_value,
                currency="EUR",
                artwork=artwork,
                url=track_url,
                store=STORE_NAME,
                store_icon="amazon",
                release_date="",
            ))

        return results
    except Exception as e:
        print(f"Amazon Music search error: {e}")
        return []
