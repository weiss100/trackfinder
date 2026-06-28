from __future__ import annotations

from urllib.parse import quote

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
            _track(2.99, store="beatport", title="Hollow Ground"),
            _track(None, store="bandcamp", title="Hollow Ground"),
            _track(1.49, store="traxsource", title="Hollow Ground"),
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
        return [_track(1.99, title="Nocturnal", artist="Joezi")]

    monkeypatch.setattr(server, "resolve_beatport_track", fake_resolver)
    monkeypatch.setattr(server, "search_all", fake_search_all)

    bp_url = "https://www.beatport.com/track/nocturnal/16659867"
    body = client.get(f"/api/search?q={bp_url}").get_json()

    assert captured["resolver_url"] == bp_url
    assert captured["search_query"] == "Joezi Nocturnal"
    assert body["query"] == "Joezi - Nocturnal"
    assert body["resolvedFrom"] == bp_url
    assert body["resolvedSource"] == "Beatport"


def test_relevant_result_outranks_cheaper_weaker_match(client, monkeypatch):
    # Both results contain every searched word (so both clear the filter), but
    # the one whose *title* matches the track name should rank above the cheaper
    # one that only scrapes by on artist/label words.
    def fake_search_all(query, selected_stores):
        return [
            # Cheaper, but "owl"/"song" land outside the title -> weaker match.
            _track(0.99, store="beatport", title="Owl", artist="Of The Trees Song"),
            # Pricier, but the title is the actual track name.
            _track(2.49, store="bandcamp", title="The Owl Song", artist="Of The Trees"),
        ]

    monkeypatch.setattr(server, "search_all", fake_search_all)

    body = client.get("/api/search?q=Of+The+Trees+The+Owl+Song").get_json()
    titles = [r["title"] for r in body["results"]]
    assert titles == ["The Owl Song", "Owl"]


def test_lookalike_results_are_filtered_out(client, monkeypatch):
    # Stores return loose matches: a search for "Yoko - Y-Axis" surfaces every
    # unrelated "Y-Axis" by other artists. None of them is the track, so the
    # response should be empty rather than a list of wrong titles.
    def fake_search_all(query, selected_stores):
        return [
            _track(1.99, store="beatport", title="Y-Axis", artist="Phil Berg"),
            _track(2.49, store="beatport", title="Axis Y", artist="A.Paul"),
            _track(1.49, store="traxsource", title="Maya", artist="Y-Axis"),
        ]

    monkeypatch.setattr(server, "search_all", fake_search_all)

    body = client.get("/api/search?q=Yoko+Y-Axis").get_json()
    assert body["results"] == []
    assert body["total"] == 0


def test_real_match_survives_filter(client, monkeypatch):
    def fake_search_all(query, selected_stores):
        return [
            _track(1.99, store="beatport", title="Y-Axis", artist="Phil Berg"),
            _track(2.49, store="beatport", title="Y-Axis", artist="Yoko"),
        ]

    monkeypatch.setattr(server, "search_all", fake_search_all)

    body = client.get("/api/search?q=Yoko+Y-Axis").get_json()
    artists = [r["artist"] for r in body["results"]]
    assert artists == ["Yoko"]


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
            _track(1.29, store="beatport", title="Track"),  # EUR -> no conversion
            TrackResult(
                title="USD Track", artist="x", label="", genre="", bpm=None, key=None,
                duration="", price="$1.29", price_value=1.29, currency="USD",
                artwork=None, url="https://x", store="x", store_icon="x", release_date="",
            ),
        ]
    monkeypatch.setattr(server, "search_all", fake_search_all)

    body = client.get("/api/search?q=track").get_json()
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


def test_results_sort_priced_then_name_your_price_then_unpriced(client, monkeypatch):
    def t(store, price, price_value):
        return TrackResult(
            title="Track", artist="Artist", label="", genre="", bpm=None, key=None,
            duration="", price=price, price_value=price_value, currency="EUR",
            artwork=None, url="https://x/" + store, store=store, store_icon=store,
            release_date="",
        )

    # Equal relevance (identical title/artist) so the price tier decides order.
    monkeypatch.setattr(server, "search_all", lambda q, s: [
        t("none", "", None),
        t("nyp", "Name Your Price", None),
        t("priced", "2.00 EUR", 2.0),
    ])

    body = client.get("/api/search?q=track").get_json()
    assert [r["store"] for r in body["results"]] == ["priced", "nyp", "none"]


def test_bandcamp_prices_resolves_and_converts_to_eur(client, monkeypatch):
    url = "https://a.bandcamp.com/track/x"
    seen = {}

    def fake_fetch_prices(urls):
        seen["urls"] = urls
        return {url: ("ab 2.00 USD", 2.0, "USD")}

    monkeypatch.setattr(server.bandcamp, "fetch_prices", fake_fetch_prices)
    monkeypatch.setattr(server, "convert_to_eur", lambda value, currency: 1.75)

    resp = client.get(f"/api/bandcamp-prices?urls={quote(url, safe='')}")
    body = resp.get_json()

    assert resp.status_code == 200
    assert seen["urls"] == [url]
    assert body[url] == {"price": "ab 2.00 USD", "priceValue": 2.0, "priceEur": 1.75}


def test_bandcamp_prices_skips_eur_conversion_for_eur_prices(client, monkeypatch):
    url = "https://a.bandcamp.com/track/y"
    monkeypatch.setattr(server.bandcamp, "fetch_prices",
                        lambda urls: {url: ("2.00 EUR", 2.0, "EUR")})
    # Must not be called for an already-EUR price.
    monkeypatch.setattr(server, "convert_to_eur",
                        lambda *a, **kw: pytest.fail("convert_to_eur called for EUR price"))

    body = client.get(f"/api/bandcamp-prices?urls={quote(url, safe='')}").get_json()

    assert "priceEur" not in body[url]
    assert body[url]["priceValue"] == 2.0
