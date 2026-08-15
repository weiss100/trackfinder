import os

from flask import Flask, jsonify, request, send_from_directory

from beatport_resolver import is_beatport_track_url, resolve_beatport_track
from fx import convert_to_eur
from ranking import matches_query, relevance
from spotify_resolver import (
    is_spotify_track_url,
    normalize_for_search,
    resolve_spotify_track,
)
from stores import bandcamp, get_store_list, search_all

app = Flask(__name__, static_folder="public", static_url_path="")


def _price_rank(r):
    """Sort key for price availability: a real price first (cheapest first),
    then name-your-price, then results carrying no price at all. Kept in sync
    with priceRank() in app.js so the client can re-sort once the Bandcamp
    prices arrive out-of-band."""
    if r.price_value and r.price_value > 0:
        return (0, r.price_value)
    if (r.price or "").strip().lower() == "name your price":
        return (1, 0.0)
    return (2, 0.0)


@app.route("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


@app.route("/api/search")
def api_search():
    q = request.args.get("q", "").strip()
    store_filter = request.args.get("stores", "")

    if not q:
        return jsonify({"results": [], "query": ""})

    original_query = q
    resolved_from = None
    resolved_source = None
    search_query = q
    # Paste a store track URL and we look up the track, then search every other
    # store for it. Built per-request so test monkeypatches on the resolvers
    # apply. Each entry is (label, matcher, resolver).
    resolvers = [
        ("Spotify", is_spotify_track_url, resolve_spotify_track),
        ("Beatport", is_beatport_track_url, resolve_beatport_track),
    ]
    resolver = next(((label, fn) for label, matches, fn in resolvers if matches(q)), None)
    if resolver:
        source, resolve = resolver
        resolved = resolve(q)
        if not resolved:
            return jsonify({
                "error": f"{source}-Link konnte nicht aufgelöst werden",
                "message": f"Track-Infos konnten von {source} nicht geladen werden.",
            }), 502
        resolved_from = q
        resolved_source = source
        q = resolved
        search_query = normalize_for_search(resolved)

    selected_stores = store_filter.split(",") if store_filter else None

    try:
        results = search_all(search_query, selected_stores)

        # Drop results that don't actually contain the searched track's words.
        # Stores return loose lookalikes (a dozen unrelated "Y-Axis" tracks for
        # "Yoko - Y-Axis"); showing nothing is better than showing those.
        results = [
            r for r in results
            if matches_query(search_query, r.title, r.artist, r.label)
        ]

        # Rank by relevance to the query first so the actually-requested track
        # rises above other songs by the same artist; price availability only
        # breaks ties between equally relevant hits (priced, then name-your-
        # price, then unpriced). Relevance is handed to the client so it can
        # re-sort identically once Bandcamp prices load out-of-band.
        scored = [
            (r, round(relevance(search_query, r.title, r.artist, r.label), 3))
            for r in results
        ]
        scored.sort(key=lambda rs: (-rs[1], *_price_rank(rs[0])))

        items = []
        for r, score in scored:
            d = r.to_dict()
            d["relevanceScore"] = score
            if r.price_value and r.price_value > 0 and (r.currency or "EUR").upper() != "EUR":
                eur = convert_to_eur(r.price_value, r.currency)
                if eur is not None:
                    d["priceEur"] = round(eur, 2)
            items.append(d)

        payload = {
            "results": items,
            "query": q,
            "total": len(items),
        }
        if resolved_from:
            payload["resolvedFrom"] = resolved_from
            payload["resolvedSource"] = resolved_source
            payload["originalQuery"] = original_query
        return jsonify(payload)
    except Exception as e:
        print(f"Search error: {e}")
        return jsonify({"error": "Search failed", "message": str(e)}), 500


@app.route("/api/stores")
def api_stores():
    return jsonify(get_store_list())


@app.route("/api/bandcamp-prices")
def api_bandcamp_prices():
    """Resolve real Bandcamp prices for a handful of track URLs. Bandcamp's
    search page carries no price, so the frontend loads these out-of-band after
    the results are already on screen (see resolveBandcampPrices in app.js)."""
    urls = request.args.getlist("urls")
    out = {}
    for url, (display, value, currency) in bandcamp.fetch_prices(urls).items():
        entry = {"price": display, "priceValue": value}
        if value and value > 0 and (currency or "EUR").upper() != "EUR":
            eur = convert_to_eur(value, currency)
            if eur is not None:
                entry["priceEur"] = round(eur, 2)
        out[url] = entry
    return jsonify(out)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 3000))
    print(f"TrackFinder running at http://localhost:{port}")
    app.run(host="0.0.0.0", port=port, debug=True)
