from __future__ import annotations

import json
import re
from typing import Optional

import requests
from bs4 import BeautifulSoup

# Matches a Beatport track URL, with or without "www" and an optional locale
# segment (e.g. /de/track/...), capturing the trailing numeric track id:
#   https://www.beatport.com/track/nocturnal/16659867
_BEATPORT_TRACK_RE = re.compile(
    r"^https?://(?:www\.)?beatport\.com/(?:[a-z]{2}/)?track/[^/]+/\d+",
    re.IGNORECASE,
)

_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml",
    "Accept-Language": "en-US,en;q=0.9",
}


def is_beatport_track_url(text: str) -> bool:
    return bool(_BEATPORT_TRACK_RE.match(text.strip()))


def _find_track_obj(queries: list) -> Optional[dict]:
    """Locate the single-track object in Beatport's dehydrated query cache.

    A track page caches the track under state.data as a dict carrying both a
    name and an artists list (the search pages instead nest a tracks list, so
    we specifically want the flat single-track shape here)."""
    for q in queries:
        data = q.get("state", {}).get("data") if isinstance(q, dict) else None
        if (
            isinstance(data, dict)
            and isinstance(data.get("artists"), list)
            and (data.get("track_name") or data.get("name"))
        ):
            return data
    return None


def resolve_beatport_track(url: str) -> Optional[str]:
    """Resolve a Beatport track URL to an "Artist - Title" search string.

    Beatport renders the track metadata server-side inside a __NEXT_DATA__ JSON
    blob. We return the base title (without the Beatport-specific mix suffix) so
    the cross-store search matches the same track elsewhere. Returns None if
    anything goes wrong.
    """
    if not is_beatport_track_url(url):
        return None

    try:
        resp = requests.get(url.strip(), headers=_HEADERS, timeout=15)
        if not resp.ok:
            return None

        soup = BeautifulSoup(resp.text, "html.parser")
        tag = soup.find("script", id="__NEXT_DATA__")
        if not tag or not tag.string:
            return None

        data = json.loads(tag.string)
        queries = (
            data.get("props", {})
            .get("pageProps", {})
            .get("dehydratedState", {})
            .get("queries", [])
        )
        track = _find_track_obj(queries)
        if not track:
            return None

        title = (track.get("track_name") or track.get("name") or "").strip()
        artist_names = [
            (a.get("artist_name") or a.get("name") or "").strip()
            for a in track.get("artists") or []
        ]
        artist = ", ".join(n for n in artist_names if n)

        if artist and title:
            return f"{artist} - {title}"
        return title or None
    except Exception as e:
        print(f"Beatport resolve error: {e}")
        return None
