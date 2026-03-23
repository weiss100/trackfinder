from __future__ import annotations

from urllib.parse import quote

import requests

from models import TrackResult

STORE_NAME = "iTunes / Apple Music"


def _format_duration(ms: int) -> str:
    mins = ms // 60000
    secs = (ms % 60000) // 1000
    return f"{mins}:{secs:02d}"


def search(query: str) -> list[TrackResult]:
    try:
        url = f"https://itunes.apple.com/search?term={quote(query)}&media=music&entity=song&limit=25"
        resp = requests.get(url, timeout=10)
        if not resp.ok:
            return []

        data = resp.json()
        results: list[TrackResult] = []

        for track in data.get("results", []):
            duration = ""
            if track.get("trackTimeMillis"):
                duration = _format_duration(track["trackTimeMillis"])

            price = "N/A"
            price_value = None
            if track.get("trackPrice"):
                price = f"{track['trackPrice']} {track.get('currency', 'USD')}"
                price_value = track["trackPrice"]

            artwork = None
            if track.get("artworkUrl100"):
                artwork = track["artworkUrl100"].replace("100x100", "200x200")

            release_date = ""
            if track.get("releaseDate"):
                release_date = track["releaseDate"].split("T")[0]

            results.append(TrackResult(
                title=track.get("trackName", ""),
                artist=track.get("artistName", ""),
                label=track.get("collectionName", ""),
                genre=track.get("primaryGenreName", ""),
                bpm=None,
                key=None,
                duration=duration,
                price=price,
                price_value=price_value,
                currency=track.get("currency", "USD"),
                artwork=artwork,
                url=track.get("trackViewUrl", ""),
                store=STORE_NAME,
                store_icon="apple",
                release_date=release_date,
            ))

        return results
    except Exception as e:
        print(f"iTunes search error: {e}")
        return []
