from __future__ import annotations

import re
from urllib.parse import quote

import requests
from bs4 import BeautifulSoup

from models import TrackResult

STORE_NAME = "Amazon Music"
_STORE_URL = "https://www.amazon.de"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml",
    "Accept-Language": "de-DE,de;q=0.9,en;q=0.8",
}


def _parse_price(text: str) -> tuple[str, float | None]:
    if not text:
        return "N/A", None
    m = re.search(r"(\d+)[,.](\d{2})", text)
    if not m:
        return text.strip(), None
    value = float(f"{m.group(1)}.{m.group(2)}")
    return f"{value:.2f} EUR", value


def _extract_artist(item) -> str:
    block = item.select_one('[data-cy="title-recipe"] .a-row.a-size-base.a-color-secondary')
    if not block:
        return ""
    text = block.get_text(" ", strip=True)
    # Amazon DE prefixes with "von " — strip it
    text = re.sub(r"^von\s+", "", text, flags=re.IGNORECASE)
    return text


def search(query: str) -> list[TrackResult]:
    try:
        url = f"{_STORE_URL}/s?k={quote(query)}&i=digital-music"
        resp = requests.get(url, headers=HEADERS, timeout=10)
        if not resp.ok:
            return []

        soup = BeautifulSoup(resp.text, "html.parser")
        results: list[TrackResult] = []

        for item in soup.select('[data-component-type="s-search-result"]')[:25]:
            h2 = item.select_one("h2")
            if not h2:
                continue
            title = h2.get("aria-label") or h2.get_text(strip=True)
            if not title:
                continue

            link_el = item.select_one('[data-cy="title-recipe"] a[href]')
            href = link_el.get("href", "") if link_el else ""
            track_url = f"{_STORE_URL}{href}" if href and not href.startswith("http") else href

            artist = _extract_artist(item)

            price_el = item.select_one(".a-price .a-offscreen") or item.select_one(".a-color-price")
            price_text = price_el.get_text(strip=True) if price_el else ""
            price, price_value = _parse_price(price_text)

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
