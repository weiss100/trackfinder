import os

from flask import Flask, jsonify, request, send_from_directory

from fx import convert_to_eur
from spotify_resolver import is_spotify_track_url, resolve_spotify_track
from stores import get_store_list, search_all

app = Flask(__name__, static_folder="public", static_url_path="")


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
    if is_spotify_track_url(q):
        resolved = resolve_spotify_track(q)
        if not resolved:
            return jsonify({
                "error": "Spotify-Link konnte nicht aufgelöst werden",
                "message": "Track-Infos konnten von Spotify nicht geladen werden.",
            }), 502
        resolved_from = q
        q = resolved

    selected_stores = store_filter.split(",") if store_filter else None

    try:
        results = search_all(q, selected_stores)

        results.sort(key=lambda r: (
            0 if r.price_value else 1,
            r.price_value or float("inf"),
        ))

        items = []
        for r in results:
            d = r.to_dict()
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
            payload["originalQuery"] = original_query
        return jsonify(payload)
    except Exception as e:
        print(f"Search error: {e}")
        return jsonify({"error": "Search failed", "message": str(e)}), 500


@app.route("/api/stores")
def api_stores():
    return jsonify(get_store_list())


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 3000))
    print(f"TrackFinder running at http://localhost:{port}")
    app.run(host="0.0.0.0", port=port, debug=True)
