from __future__ import annotations

from models import TrackResult
from stores import _dedupe


def _track(title, artist, store, price_value):
    return TrackResult(
        title=title, artist=artist, label="", genre="", bpm=None, key=None,
        duration="", price=str(price_value), price_value=price_value,
        currency="EUR", artwork=None, url="https://x", store=store,
        store_icon=store, release_date="",
    )


def test_same_track_in_one_store_collapses_to_cheapest():
    out = _dedupe([
        _track("The Owl Song", "Of The Trees", "Amazon Music", 1.29),
        _track("The Owl Song", "Of The Trees", "Amazon Music", 0.99),
        _track("The Owl Song", "Of The Trees", "Amazon Music", 1.49),
    ])
    assert len(out) == 1
    assert out[0].price_value == 0.99


def test_same_track_across_stores_is_kept():
    out = _dedupe([
        _track("The Owl Song", "Of The Trees", "Amazon Music", 1.29),
        _track("The Owl Song", "Of The Trees", "Beatport", 1.39),
    ])
    assert len(out) == 2


def test_dedupe_ignores_case_and_whitespace():
    out = _dedupe([
        _track("The Owl Song", "Of The Trees", "Amazon Music", 1.29),
        _track("the  owl song", "OF THE TREES", "Amazon Music", 0.99),
    ])
    assert len(out) == 1
    assert out[0].price_value == 0.99


def test_first_seen_order_is_preserved():
    out = _dedupe([
        _track("B Side", "X", "Amazon Music", 2.00),
        _track("A Side", "X", "Amazon Music", 2.00),
        _track("B Side", "X", "Amazon Music", 1.00),  # cheaper dup of first
    ])
    assert [r.title for r in out] == ["B Side", "A Side"]
    assert out[0].price_value == 1.00


def test_unpriced_duplicate_does_not_replace_priced_one():
    out = _dedupe([
        _track("Track", "X", "Bandcamp", 1.50),
        TrackResult(
            title="Track", artist="X", label="", genre="", bpm=None, key=None,
            duration="", price="N/A", price_value=None, currency="EUR",
            artwork=None, url="https://x", store="Bandcamp", store_icon="Bandcamp",
            release_date="",
        ),
    ])
    assert len(out) == 1
    assert out[0].price_value == 1.50
