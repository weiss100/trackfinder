from __future__ import annotations

import pytest

from beatport_resolver import _find_track_obj, is_beatport_track_url


@pytest.mark.parametrize("url", [
    "https://www.beatport.com/track/nocturnal/16659867",
    "http://beatport.com/track/nocturnal/16659867",
    "https://www.beatport.com/de/track/nocturnal/16659867",
    "https://www.beatport.com/track/some-long-slug-name/123",
])
def test_recognizes_beatport_track_urls(url):
    assert is_beatport_track_url(url)


@pytest.mark.parametrize("url", [
    "https://www.beatport.com/release/foo/123",          # release, not a track
    "https://www.beatport.com/artist/joezi/123",         # artist page
    "https://open.spotify.com/track/abc",                # other store
    "nocturnal",                                          # plain text query
    "https://www.beatport.com/track/nocturnal",          # missing id
])
def test_rejects_non_track_urls(url):
    assert not is_beatport_track_url(url)


def test_find_track_obj_picks_flat_single_track_shape():
    queries = [
        {"state": {"data": {"tracks": {"data": [{"track_name": "X"}]}}}},  # search shape
        {"state": {"data": {"track_name": "Nocturnal", "artists": [{"artist_name": "Joezi"}]}}},
    ]
    track = _find_track_obj(queries)
    assert track is not None
    assert track["track_name"] == "Nocturnal"


def test_find_track_obj_returns_none_when_absent():
    assert _find_track_obj([{"state": {"data": {"unrelated": True}}}]) is None
