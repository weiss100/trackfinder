from __future__ import annotations

import json

import pytest

import spotify_resolver
from spotify_resolver import is_spotify_track_url, resolve_spotify_track


class FakeResponse:
    def __init__(self, text: str = "", status_code: int = 200):
        self.text = text
        self.status_code = status_code

    @property
    def ok(self) -> bool:
        return 200 <= self.status_code < 300


def _embed_html(entity: dict) -> str:
    payload = {"props": {"pageProps": {"state": {"data": {"entity": entity}}}}}
    return (
        "<html><body>"
        f'<script id="__NEXT_DATA__" type="application/json">{json.dumps(payload)}</script>'
        "</body></html>"
    )


@pytest.mark.parametrize("url", [
    "https://open.spotify.com/track/0D3R3tViQUgPvuzcVX5Yku",
    "https://open.spotify.com/intl-de/track/0D3R3tViQUgPvuzcVX5Yku",
    "https://open.spotify.com/intl-de/track/0D3R3tViQUgPvuzcVX5Yku?si=07223e583ecb4d36",
    "http://open.spotify.com/track/abc123",
    "  https://open.spotify.com/track/abc123  ",
])
def test_is_spotify_track_url_accepts_valid(url):
    assert is_spotify_track_url(url) is True


@pytest.mark.parametrize("text", [
    "",
    "hello world",
    "https://open.spotify.com/album/0D3R3tViQUgPvuzcVX5Yku",
    "https://open.spotify.com/playlist/abc",
    "https://example.com/track/abc",
    "spotify:track:0D3R3tViQUgPvuzcVX5Yku",
])
def test_is_spotify_track_url_rejects_invalid(text):
    assert is_spotify_track_url(text) is False


def test_resolve_returns_artist_dash_title(monkeypatch):
    entity = {
        "name": "Hollow Ground",
        "artists": [{"name": "NOTSOBAD"}, {"name": "Able Faces"}],
    }
    captured = {}

    def fake_get(url, headers=None, timeout=None):
        captured["url"] = url
        return FakeResponse(_embed_html(entity))

    monkeypatch.setattr(spotify_resolver.requests, "get", fake_get)

    result = resolve_spotify_track(
        "https://open.spotify.com/intl-de/track/0D3R3tViQUgPvuzcVX5Yku?si=07223e583ecb4d36"
    )

    assert result == "NOTSOBAD, Able Faces - Hollow Ground"
    assert captured["url"] == "https://open.spotify.com/embed/track/0D3R3tViQUgPvuzcVX5Yku"


def test_resolve_strips_locale_and_query_for_embed_url(monkeypatch):
    captured = {}

    def fake_get(url, headers=None, timeout=None):
        captured["url"] = url
        return FakeResponse(_embed_html({"name": "X", "artists": [{"name": "A"}]}))

    monkeypatch.setattr(spotify_resolver.requests, "get", fake_get)

    resolve_spotify_track("https://open.spotify.com/intl-fr/track/zzz?si=abc")

    assert captured["url"] == "https://open.spotify.com/embed/track/zzz"


def test_resolve_returns_title_only_when_no_artist(monkeypatch):
    html = _embed_html({"name": "Lonely Track", "artists": []})
    monkeypatch.setattr(
        spotify_resolver.requests, "get",
        lambda *a, **kw: FakeResponse(html),
    )

    assert resolve_spotify_track("https://open.spotify.com/track/xyz") == "Lonely Track"


def test_resolve_returns_none_for_non_track_url(monkeypatch):
    called = {"n": 0}

    def fake_get(*a, **kw):
        called["n"] += 1
        return FakeResponse("")

    monkeypatch.setattr(spotify_resolver.requests, "get", fake_get)

    assert resolve_spotify_track("https://example.com/foo") is None
    assert called["n"] == 0  # no HTTP made


def test_resolve_returns_none_on_http_error(monkeypatch):
    monkeypatch.setattr(
        spotify_resolver.requests, "get",
        lambda *a, **kw: FakeResponse("server boom", status_code=500),
    )

    assert resolve_spotify_track("https://open.spotify.com/track/abc") is None


def test_resolve_returns_none_when_next_data_missing(monkeypatch):
    monkeypatch.setattr(
        spotify_resolver.requests, "get",
        lambda *a, **kw: FakeResponse("<html><body>no script here</body></html>"),
    )

    assert resolve_spotify_track("https://open.spotify.com/track/abc") is None


def test_resolve_returns_none_on_malformed_json(monkeypatch):
    html = '<script id="__NEXT_DATA__" type="application/json">{not json</script>'
    monkeypatch.setattr(
        spotify_resolver.requests, "get",
        lambda *a, **kw: FakeResponse(html),
    )

    assert resolve_spotify_track("https://open.spotify.com/track/abc") is None


def test_resolve_returns_none_when_request_raises(monkeypatch):
    def boom(*a, **kw):
        raise RuntimeError("network down")

    monkeypatch.setattr(spotify_resolver.requests, "get", boom)

    assert resolve_spotify_track("https://open.spotify.com/track/abc") is None
