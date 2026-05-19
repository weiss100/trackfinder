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

_PRICE_RE = re.compile(r"([£€$])\s*(\d+[.,]\d{2})")
_CURRENCY_BY_SYMBOL = {"£": "GBP", "€": "EUR", "$": "USD"}


def _parse_price(text: str):
    if not text:
        return text or "N/A", None, "GBP"
    m = _PRICE_RE.search(text)
    if not m:
        return text.strip(), None, "GBP"
    symbol, num = m.group(1), m.group(2).replace(",", ".")
    try:
        value = float(num)
    except ValueError:
        return text.strip(), None, "GBP"
    currency = _CURRENCY_BY_SYMBOL.get(symbol, "GBP")
    return f"{symbol}{value:.2f}", value, currency


def search(query: str) -> list[TrackResult]:
    try:
        url = f"{_STORE_URL}/search/?q%5Ball%5D%5B%5D={quote(query)}&solrorder=relevancy"
        resp = requests.get(url, headers=_HEADERS, timeout=10)
        if not resp.ok:
            return []

        soup = BeautifulSoup(resp.text, "html.parser")
        results: list[TrackResult] = []

        for el in soup.select(".jd-listing-item"):
            title_el = el.select_one(".juno-title")
            if not title_el:
                continue
            title = title_el.get_text(strip=True)
            link = title_el.get("href", "")
            if not title or not link:
                continue

            artist = ", ".join(a.get_text(strip=True) for a in el.select(".juno-artist a"))
            label_el = el.select_one(".juno-label")
            label = label_el.get_text(strip=True) if label_el else ""

            price_el = el.select_one("a.btn-cta")
            price_text = price_el.get_text(" ", strip=True) if price_el else ""
            price, price_value, currency = _parse_price(price_text)

            genre = ""
            release_date = ""
            meta_el = el.select_one(".text-muted")
            if meta_el:
                for line in [s.strip() for s in meta_el.stripped_strings]:
                    if re.match(r"^\d{1,2}\s+[A-Za-z]{3}\s+\d{2,4}$", line):
                        release_date = line
                    elif "/" in line or "House" in line or "Techno" in line or "Trance" in line:
                        genre = line

            img_el = el.select_one("img.li-img")
            img = None
            if img_el:
                img = img_el.get("src") or img_el.get("data-src")

            full_url = link if link.startswith("http") else f"{_STORE_URL}{link}"

            results.append(TrackResult(
                title=title,
                artist=artist,
                label=label,
                genre=genre,
                bpm=None,
                key=None,
                duration="",
                price=price,
                price_value=price_value,
                currency=currency,
                artwork=img,
                url=full_url,
                store=STORE_NAME,
                store_icon="juno",
                release_date=release_date,
            ))

            if len(results) >= 25:
                break

        return results
    except Exception as e:
        print(f"Juno Download search error: {e}")
        return []
