from __future__ import annotations

import json
import re
from typing import Optional

import requests

_SPOTIFY_TRACK_RE = re.compile(
    r"^https?://open\.spotify\.com/(?:intl-[a-z-]+/)?track/([A-Za-z0-9]+)",
    re.IGNORECASE,
)

_NEXT_DATA_RE = re.compile(
    r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>',
    re.S,
)

_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)


def is_spotify_track_url(text: str) -> bool:
    return bool(_SPOTIFY_TRACK_RE.match(text.strip()))


def resolve_spotify_track(url: str) -> Optional[str]:
    """Resolve a Spotify track URL to an "Artist - Title" search string.

    Uses Spotify's public embed page, which renders track metadata server-side
    inside a __NEXT_DATA__ JSON blob. Returns None if anything goes wrong.
    """
    match = _SPOTIFY_TRACK_RE.match(url.strip())
    if not match:
        return None

    track_id = match.group(1)
    embed_url = f"https://open.spotify.com/embed/track/{track_id}"

    try:
        resp = requests.get(
            embed_url,
            headers={"User-Agent": _UA, "Accept-Language": "en"},
            timeout=10,
        )
        if not resp.ok:
            return None

        m = _NEXT_DATA_RE.search(resp.text)
        if not m:
            return None

        data = json.loads(m.group(1))
        entity = data["props"]["pageProps"]["state"]["data"]["entity"]

        title = (entity.get("name") or entity.get("title") or "").strip()
        artists = entity.get("artists") or []
        artist_names = [a.get("name", "").strip() for a in artists if a.get("name")]
        artist = ", ".join(artist_names)

        if artist and title:
            return f"{artist} - {title}"
        return title or None
    except Exception as e:
        print(f"Spotify resolve error: {e}")
        return None
