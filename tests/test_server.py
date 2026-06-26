from __future__ import annotations

import pytest

import server
from models import TrackResult


def _track(price_value, store="beatport", title="t", artist="a"):
    return TrackResult(
        title=title, artist=artist, label="", genre="", bpm=None, key=None,
        duration="", price=str(price_value) if price_value else "N/A",
        price_value=price_value, currency="EUR", artwork=None,
        url="https://x", store=store, store_icon=store, release_date="",
    )


@pytest.fixture
def client():
    server.app.config["TESTING"] = True
    return server.app.test_client()


def test_empty_query_returns_empty_results(client):
    resp = client.get("/api/search?q=")
    assert resp.status_code == 200
    assert resp.get_json() == {"results": [], "query": ""}


def test_plain_query_passes_through_and_sorts_by_price(client, monkeypatch):
    captured = {}

    def fake_search_all(query, selected_stores):
        captured["query"] = query
        captured["stores"] = selected_stores
        return [
            _track(2.99, store="beatport"),
            _track(None, store="bandcamp"),
            _track(1.49, store="traxsource"),
        ]

    monkeypatch.setattr(server, "search_all", fake_search_all)

    resp = client.get("/api/search?q=hollow+ground&stores=beatport,traxsource")
    body = resp.get_json()

    assert resp.status_code == 200
    assert captured["query"] == "hollow ground"
    assert captured["stores"] == ["beatport", "traxsource"]
    assert [r["priceValue"] for r in body["results"]] == [1.49, 2.99, None]
    assert body["query"] == "hollow ground"
    assert body["total"] == 3
    assert "resolvedFrom" not in body


def test_beatport_url_is_resolved_before_search(client, monkeypatch):
    captured = {}

    def fake_resolver(url):
        captured["resolver_url"] = url
        return "Joezi - Nocturnal"

    def fake_search_all(query, selected_stores):
        captured["search_query"] = query
        return [_track(1.99)]

    monkeypatch.setattr(server, "resolve_beatport_track", fake_resolver)
    monkeypatch.setattr(server, "search_all", fake_search_all)

    bp_url = "https://www.beatport.com/track/nocturnal/16659867"
    body = client.get(f"/api/search?q={bp_url}").get_json()

    assert captured["resolver_url"] == bp_url
    assert captured["search_query"] == "Joezi Nocturnal"
    assert body["query"] == "Joezi - Nocturnal"
    assert body["resolvedFrom"] == bp_url
    assert body["resolvedSource"] == "Beatport"


def test_relevant_result_outranks_cheaper_irrelevant_one(client, monkeypatch):
    def fake_search_all(query, selected_stores):
        return [
            # Cheaper, but only matches the artist — not the requested title.
            _track(0.99, store="beatport", title="Some Other Song", artist="Of The Trees"),
            # Pricier, but the actual track the user searched for.
            _track(2.49, store="bandcamp", title="The Owl Song", artist="Of The Trees"),
        ]

    monkeypatch.setattr(server, "search_all", fake_search_all)

    body = client.get("/api/search?q=Of+The+Trees+The+Owl+Song").get_json()
    titles = [r["title"] for r in body["results"]]
    assert titles == ["The Owl Song", "Some Other Song"]


def test_spotify_url_is_resolved_before_search(client, monkeypatch):
    captured = {}

    def fake_resolver(url):
        captured["resolver_url"] = url
        return "NOTSOBAD, Able Faces - Hollow Ground"

    def fake_search_all(query, selected_stores):
        captured["search_query"] = query
        return [_track(1.99)]

    monkeypatch.setattr(server, "resolve_spotify_track", fake_resolver)
    monkeypatch.setattr(server, "search_all", fake_search_all)

    spotify_url = "https://open.spotify.com/intl-de/track/0D3R3tViQUgPvuzcVX5Yku?si=abc"
    resp = client.get(f"/api/search?q={spotify_url}")
    body = resp.get_json()

    assert resp.status_code == 200
    assert captured["resolver_url"] == spotify_url
    # Stores receive the slim form — primary artist only, no separators — so
    # strict matchers like Amazon's can find the track.
    assert captured["search_query"] == "NOTSOBAD Hollow Ground"
    # User-facing query keeps the pretty resolved form for display.
    assert body["query"] == "NOTSOBAD, Able Faces - Hollow Ground"
    assert body["resolvedFrom"] == spotify_url
    assert body["originalQuery"] == spotify_url


def test_spotify_url_resolution_failure_returns_502(client, monkeypatch):
    monkeypatch.setattr(server, "resolve_spotify_track", lambda url: None)

    called = {"n": 0}
    def should_not_run(*a, **kw):
        called["n"] += 1
        return []
    monkeypatch.setattr(server, "search_all", should_not_run)

    resp = client.get("/api/search?q=https://open.spotify.com/track/abc")

    assert resp.status_code == 502
    assert "error" in resp.get_json()
    assert called["n"] == 0


def test_non_eur_results_get_price_eur_injected(client, monkeypatch):
    monkeypatch.setattr(server, "convert_to_eur", lambda value, currency: 1.18 if currency == "USD" else None)

    def fake_search_all(query, selected_stores):
        return [
            _track(1.29, store="beatport"),  # EUR -> no conversion
            TrackResult(
                title="USD track", artist="x", label="", genre="", bpm=None, key=None,
                duration="", price="$1.29", price_value=1.29, currency="USD",
                artwork=None, url="https://x", store="x", store_icon="x", release_date="",
            ),
        ]
    monkeypatch.setattr(server, "search_all", fake_search_all)

    body = client.get("/api/search?q=q").get_json()
    by_store = {r["store"]: r for r in body["results"]}

    assert "priceEur" not in by_store["beatport"]
    assert by_store["x"]["priceEur"] == 1.18


def test_search_error_returns_500(client, monkeypatch):
    def boom(*a, **kw):
        raise RuntimeError("kaputt")
    monkeypatch.setattr(server, "search_all", boom)

    resp = client.get("/api/search?q=anything")
    assert resp.status_code == 500
    assert resp.get_json()["error"] == "Search failed"


def test_stores_endpoint_lists_known_stores(client):
    resp = client.get("/api/stores")
    body = resp.get_json()
    keys = {s["key"] for s in body}

    assert resp.status_code == 200
    assert {"beatport", "traxsource", "bandcamp", "amazon"} <= keys
    assert "itunes" not in keys
    assert "juno" not in keys
