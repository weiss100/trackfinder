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


def _format_duration(ms: int) -> str:
    total = ms // 1000
    return f"{total // 60}:{total % 60:02d}"


def _slug(text: str) -> str:
    text = re.sub(r"[^\w\s-]", "", text.lower())
    return re.sub(r"\s+", "-", text.strip()) or "track"


def _find_tracks_list(queries: list) -> list:
    for q in queries:
        try:
            tracks = q["state"]["data"]["tracks"]
        except (KeyError, TypeError):
            continue
        if isinstance(tracks, dict) and isinstance(tracks.get("data"), list):
            return tracks["data"]
        if isinstance(tracks, list):
            return tracks
    return []


def _build_track(t: dict) -> TrackResult | None:
    track_id = t.get("track_id")
    title = t.get("track_name") or t.get("name") or ""
    if not track_id or not title:
        return None

    mix = t.get("mix_name") or ""
    display_title = f"{title} ({mix})" if mix and mix.lower() != "original mix" else title

    artists = ", ".join(a.get("artist_name", "") for a in t.get("artists") or []).strip(", ")

    label = ""
    if isinstance(t.get("label"), dict):
        label = t["label"].get("label_name", "")

    genres = t.get("genre") or []
    genre = genres[0].get("genre_name", "") if genres and isinstance(genres[0], dict) else ""

    bpm = str(t["bpm"]) if t.get("bpm") else None
    key = t.get("key_name") or None

    duration = _format_duration(t["length"]) if isinstance(t.get("length"), int) else ""

    price_obj = t.get("price") or {}
    price_value = price_obj.get("value") if isinstance(price_obj, dict) else None
    currency = price_obj.get("code", "USD") if isinstance(price_obj, dict) else "USD"
    price_display = price_obj.get("display") if isinstance(price_obj, dict) else None
    price = price_display or (f"{price_value:.2f} {currency}" if price_value else "N/A")

    artwork = None
    release = t.get("release") or {}
    if isinstance(release, dict):
        artwork = release.get("release_image_uri")
    if not artwork:
        artwork = t.get("track_image_uri")

    release_date = (t.get("publish_date") or t.get("release_date") or "")
    if isinstance(release_date, str):
        release_date = release_date.split("T")[0]

    url = f"{_STORE_URL}/track/{_slug(title)}/{track_id}"

    return TrackResult(
        title=display_title,
        artist=artists,
        label=label,
        genre=genre,
        bpm=bpm,
        key=key,
        duration=duration,
        price=price,
        price_value=price_value,
        currency=currency,
        artwork=artwork,
        url=url,
        store=STORE_NAME,
        store_icon="beatport",
        release_date=release_date,
    )


def search(query: str) -> list[TrackResult]:
    try:
        url = f"{_STORE_URL}/search?q={quote(query)}"
        resp = requests.get(url, headers=_HEADERS, timeout=10)
        if not resp.ok:
            return []

        soup = BeautifulSoup(resp.text, "html.parser")
        tag = soup.find("script", id="__NEXT_DATA__")
        if not tag or not tag.string:
            return []

        data = json.loads(tag.string)
        queries = data.get("props", {}).get("pageProps", {}).get("dehydratedState", {}).get("queries", [])
        tracks = _find_tracks_list(queries)

        results: list[TrackResult] = []
        for t in tracks[:25]:
            built = _build_track(t)
            if built:
                results.append(built)
        return results
    except Exception as e:
        print(f"Beatport search error: {e}")
        return []
