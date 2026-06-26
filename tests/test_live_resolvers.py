"""Live smoke tests for external resolvers and store search modules.

These tests hit the real network and exist so that a silently broken scraper
(HTML structure changed, API moved, etc.) becomes visible. They are skipped by
default; run them explicitly with:

    pytest -m live

A single failure here means the relevant resolver needs attention before it
silently returns zero results in production.
"""
from __future__ import annotations

import pytest

from models import TrackResult
from spotify_resolver import resolve_spotify_track
from stores import amazon_music, bandcamp, beatport, traxsource

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


def test_bandcamp_live():
    """Bandcamp needs Playwright + a browser to clear its Fastly challenge.

    Skip (rather than fail) when neither is installed, so the absence of a
    browser on a given machine doesn't masquerade as a scraper regression.
    """
    html = bandcamp.fetch(QUERY)
    if html is None:
        pytest.skip("Bandcamp unavailable: Playwright or a browser is not installed here")
    _assert_track_results(bandcamp.parse(html), "bandcamp")


# Amazon throttles datacenter IPs (e.g. CI runners) with an HTTP 503
# "Tut uns Leid!" bot page that carries no listings, so the scraper correctly
# returns []. Detect that block from the same response we parse — a second
# request could disagree, since the throttle is per-request — and skip rather
# than fail, so a real markup regression (200 page, 0 results) still goes red
# while a CI-only IP block does not.
_AMAZON_BOT_WALL_MARKERS = (
    "to discuss automated access to amazon data",
    "enter the characters you see below",
    "/errors/validatecaptcha",
)


def test_amazon_music_live():
    resp = amazon_music.fetch(QUERY)
    body = resp.text.lower()
    if resp.status_code == 503 or any(m in body for m in _AMAZON_BOT_WALL_MARKERS):
        pytest.skip(f"Amazon throttled this IP (HTTP {resp.status_code} bot page), not a scraper regression")
    _assert_track_results(amazon_music.parse(resp.text), "amazon_music")
