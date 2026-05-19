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
from stores import amazon_music, bandcamp, beatport, itunes, juno, traxsource

pytestmark = pytest.mark.live

QUERY = "daft punk one more time"


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


def test_juno_live():
    _assert_track_results(juno.search(QUERY), "juno")


def test_bandcamp_live():
    _assert_track_results(bandcamp.search(QUERY), "bandcamp")


def test_itunes_live():
    _assert_track_results(itunes.search(QUERY), "itunes")


def test_amazon_music_live():
    _assert_track_results(amazon_music.search(QUERY), "amazon_music")
