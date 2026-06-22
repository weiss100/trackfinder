"""Live smoke tests for external resolvers and store search modules.

These tests hit the real network and exist so that a silently broken scraper
(HTML structure changed, API moved, etc.) becomes visible. They are skipped by
default; run them explicitly with:

    pytest -m live

A single failure here means the relevant resolver needs attention before it
silently returns zero results in production.
"""
from __future__ import annotations

from urllib.parse import quote

import pytest
import requests

from models import TrackResult
from spotify_resolver import resolve_spotify_track
from stores import amazon_music, beatport, itunes, traxsource

pytestmark = pytest.mark.live

# Generic genre term — hits every store regardless of catalog focus.
# Don't change this to an artist name; specialty stores (Traxsource etc.)
# won't carry every act and the live test will go red for no reason.
QUERY = "techno"


def _assert_track_results(results, store_label: str):
    assert isinstance(results, list), f"{store_label}: not a list"
    assert len(results) > 0, f"{store_label}: zero results for '{QUERY}' — scraper likely broken"
    for r in results:
        assert isinstance(r, TrackResult), f"{store_label}: wrong type {type(r)}"
        assert r.title, f"{store_label}: result with empty title — {r}"
        assert r.url, f"{store_label}: result with empty url — {r}"


def test_spotify_resolver_live():
    """Spotify embed page still exposes track metadata in __NEXT_DATA__."""
    url = "https://open.spotify.com/intl-de/track/0D3R3tViQUgPvuzcVX5Yku?si=07223e583ecb4d36"
    result = resolve_spotify_track(url)

    assert result is not None, "Spotify resolver returned None — embed page format may have changed"
    assert "Hollow Ground" in result, f"unexpected title in '{result}'"
    # at least one of the known artists must show up
    assert "NOTSOBAD" in result or "Able Faces" in result, f"no known artist in '{result}'"


def test_beatport_live():
    _assert_track_results(beatport.search(QUERY), "beatport")


def test_traxsource_live():
    _assert_track_results(traxsource.search(QUERY), "traxsource")


def test_itunes_live():
    _assert_track_results(itunes.search(QUERY), "itunes")


# Amazon serves a captcha/bot-check page to datacenter IPs (e.g. CI runners)
# instead of search results. That HTTP 200 page carries no listings, so the
# scraper correctly returns []. These markers let us tell that IP block apart
# from a genuine markup regression so CI doesn't go red on something that works
# fine from a normal residential IP.
_AMAZON_BOT_WALL_MARKERS = (
    "enter the characters you see below",
    "type the characters you see in this image",
    "to discuss automated access to amazon data",
    "/errors/validatecaptcha",
    "not a robot",
)


def _amazon_is_bot_walled() -> bool:
    url = f"{amazon_music._STORE_URL}/s?k={quote(QUERY)}&i=digital-music"
    try:
        body = requests.get(url, headers=amazon_music.HEADERS, timeout=10).text.lower()
    except requests.RequestException:
        return False
    return any(marker in body for marker in _AMAZON_BOT_WALL_MARKERS)


def test_amazon_music_live():
    results = amazon_music.search(QUERY)
    if not results:
        # TEMP DIAGNOSTIC: surface exactly what Amazon serves the CI runner.
        import re as _re
        url = f"{amazon_music._STORE_URL}/s?k={quote(QUERY)}&i=digital-music"
        resp = requests.get(url, headers=amazon_music.HEADERS, timeout=10)
        body = resp.text
        title = _re.search(r"<title>(.*?)</title>", body, _re.S | _re.I)
        title = title.group(1).strip()[:120] if title else "<none>"
        snippet = _re.sub(r"\s+", " ", body)[:600]
        raise AssertionError(
            f"AMAZON-DIAG status={resp.status_code} len={len(body)} "
            f"hits={[m for m in _AMAZON_BOT_WALL_MARKERS if m in body.lower()]} "
            f"title={title!r} snippet={snippet!r}"
        )
    if not results and _amazon_is_bot_walled():
        pytest.skip("Amazon served a bot-check page (datacenter IP block), not a scraper regression")
    _assert_track_results(results, "amazon_music")
