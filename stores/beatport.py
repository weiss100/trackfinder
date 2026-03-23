from __future__ import annotations

import json
import re
from urllib.parse import quote

import requests
from bs4 import BeautifulSoup

from models import TrackResult

STORE_NAME = "Beatport"
_STORE_URL = "https://www.beatport.com"
_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml",
    "Accept-Language": "en-US,en;q=0.9",
}


def _format_duration(seconds: int) -> str:
    mins = seconds // 60
    secs = seconds % 60
    return f"{mins}:{secs:02d}"


def _parse_price(s: str) -> float | None:
    m = re.search(r"[\d.]+", s)
    return float(m.group()) if m else None


def _extract_tracks(data, results: list[TrackResult] | None = None) -> list[TrackResult]:
    if results is None:
        results = []
    if data is None or not isinstance(data, (dict, list)):
        return results

    if isinstance(data, list):
        for item in data:
            _extract_tracks(item, results)
        return results

    obj = data
    if obj.get("name") and (obj.get("artists") or obj.get("artist")) and (obj.get("slug") or obj.get("id")):
        artists_list = obj.get("artists")
        artist_obj = obj.get("artist")
        if artists_list:
            artist_names = ", ".join(a.get("name", str(a)) if isinstance(a, dict) else str(a) for a in artists_list)
        elif isinstance(artist_obj, dict):
            artist_names = artist_obj.get("name", "")
        else:
            artist_names = str(artist_obj or "")

        label = obj.get("label") or {}
        release = obj.get("release") or {}
        genre_obj = obj.get("genre") or {}
        genres = obj.get("genres") or []
        key_obj = obj.get("key")
        price_obj = obj.get("price") or {}
        image = obj.get("image") or {}
        date_obj = obj.get("date") or {}

        label_name = label.get("name", "") if isinstance(label, dict) else ""
        if not label_name and isinstance(release, dict):
            rl = release.get("label")
            label_name = rl.get("name", "") if isinstance(rl, dict) else ""

        genre_name = genre_obj.get("name", "") if isinstance(genre_obj, dict) else ""
        if not genre_name and genres:
            genre_name = genres[0].get("name", "") if isinstance(genres[0], dict) else ""

        key_name = key_obj.get("name") if isinstance(key_obj, dict) else key_obj
        price_val = price_obj.get("value") if isinstance(price_obj, dict) else None
        price_cur = price_obj.get("currency", "USD") if isinstance(price_obj, dict) else "USD"
        img_uri = image.get("uri") if isinstance(image, dict) else None
        if not img_uri and isinstance(release, dict):
            ri = release.get("image")
            img_uri = ri.get("uri") if isinstance(ri, dict) else None

        length = obj.get("length")
        duration = _format_duration(int(length)) if isinstance(length, (int, float)) else ""

        results.append(TrackResult(
            title=str(obj.get("name") or obj.get("title") or ""),
            artist=artist_names,
            label=label_name,
            genre=genre_name,
            bpm=str(obj["bpm"]) if obj.get("bpm") else None,
            key=key_name or None,
            duration=duration,
            price=f"${price_val / 100:.2f}" if price_val else "$1.29",
            price_value=price_val / 100 if price_val else 1.29,
            currency=price_cur,
            artwork=img_uri,
            url=f"{_STORE_URL}/track/{obj.get('slug')}/{obj.get('id')}" if obj.get("slug") else _STORE_URL,
            store=STORE_NAME,
            store_icon="beatport",
            release_date=date_obj.get("published", "") if isinstance(date_obj, dict) else str(obj.get("publish_date", "")),
        ))
    else:
        for val in obj.values():
            if isinstance(val, (dict, list)) and len(results) < 25:
                _extract_tracks(val, results)

    return results


def search(query: str) -> list[TrackResult]:
    try:
        url = f"{_STORE_URL}/search?q={quote(query)}"
        resp = requests.get(url, headers=_HEADERS, timeout=10)
        if not resp.ok:
            return []

        html = resp.text
        soup = BeautifulSoup(html, "html.parser")
        results: list[TrackResult] = []

        # Try __NEXT_DATA__ first
        page_data = None
        tag = soup.find("script", id="__NEXT_DATA__")
        if tag and tag.string:
            try:
                parsed = json.loads(tag.string)
                page_data = parsed.get("props", {}).get("pageProps")
            except (json.JSONDecodeError, AttributeError):
                pass

        # Try other JSON scripts
        if not page_data:
            for script in soup.find_all("script", {"type": "application/json"}):
                try:
                    text = script.string
                    if text and "tracks" in text:
                        page_data = json.loads(text)
                        break
                except (json.JSONDecodeError, AttributeError):
                    pass

        if page_data:
            return _extract_tracks(page_data)[:25]

        # Fallback: parse HTML
        for el in soup.select('[data-testid="track-row"], .track-row, .bucket-item'):
            title_el = el.select_one('.track-title, [data-testid="track-title"]')
            title = title_el.get_text(strip=True) if title_el else ""
            artist_el = el.select_one('.track-artists, [data-testid="track-artists"]')
            artist = artist_el.get_text(strip=True) if artist_el else ""
            price_el = el.select_one('.add-to-cart-btn, .price, [data-testid="price"]')
            price_text = price_el.get_text(strip=True) if price_el else ""
            link_el = el.select_one('a[href*="/track/"]')
            link = link_el["href"] if link_el else None

            if title:
                label_el = el.select_one('.track-label, [data-testid="track-label"]')
                genre_el = el.select_one('.track-genre, [data-testid="track-genre"]')
                bpm_el = el.select_one('.track-bpm, [data-testid="track-bpm"]')
                key_el = el.select_one('.track-key, [data-testid="track-key"]')
                dur_el = el.select_one('.track-duration, [data-testid="track-duration"]')
                img_el = el.select_one("img")

                results.append(TrackResult(
                    title=title,
                    artist=artist,
                    label=label_el.get_text(strip=True) if label_el else "",
                    genre=genre_el.get_text(strip=True) if genre_el else "",
                    bpm=bpm_el.get_text(strip=True) if bpm_el else None,
                    key=key_el.get_text(strip=True) if key_el else None,
                    duration=dur_el.get_text(strip=True) if dur_el else "",
                    price=price_text or "$1.29",
                    price_value=_parse_price(price_text or "$1.29"),
                    currency="USD",
                    artwork=img_el["src"] if img_el and img_el.get("src") else None,
                    url=f"{_STORE_URL}{link}" if link else f"{_STORE_URL}/search?q={quote(query)}",
                    store=STORE_NAME,
                    store_icon="beatport",
                    release_date="",
                ))

        return results
    except Exception as e:
        print(f"Beatport search error: {e}")
        return []
