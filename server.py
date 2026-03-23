import os

from flask import Flask, jsonify, request, send_from_directory

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

    selected_stores = store_filter.split(",") if store_filter else None

    try:
        results = search_all(q, selected_stores)

        results.sort(key=lambda r: (
            0 if r.price_value else 1,
            r.price_value or float("inf"),
        ))

        return jsonify({
            "results": [r.to_dict() for r in results],
            "query": q,
            "total": len(results),
        })
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
