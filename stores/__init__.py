from __future__ import annotations

import concurrent.futures
from typing import Optional

from models import TrackResult
from stores import beatport, traxsource, amazon_music, bandcamp

# Bandcamp's search is served behind a Fastly bot-management challenge that
# needs a real JS runtime to solve, so its module drives headless Chrome via
# Playwright (see stores/bandcamp.py). Requires `playwright` + a browser; if
# those are missing it degrades to zero results instead of erroring.
#
# Juno Download was removed after the store shut down in 2026 (its search now
# redirects to a captcha-gated homepage). Volumo is its suggested successor and
# a likely replacement via its public JSON API at volumo.com/api/v1.

_STORES: dict[str, object] = {
    "beatport": beatport,
    "traxsource": traxsource,
    "bandcamp": bandcamp,
    "amazon": amazon_music,
}


def _dedupe(results: list[TrackResult]) -> list[TrackResult]:
    """Collapse duplicate listings of the same track *within* a store.

    Amazon in particular returns the same track under several ASINs, so the
    same title/artist shows up multiple times. Keep one entry per
    (store, title, artist) — the cheapest, since that's the price worth
    comparing — while preserving first-seen order. Duplicates across different
    stores are intentionally kept: comparing their prices is the point.
    """
    best: dict[tuple[str, str, str], TrackResult] = {}
    order: list[tuple[str, str, str]] = []

    def _norm(s: str) -> str:
        return " ".join((s or "").lower().split())

    for r in results:
        key = (r.store, _norm(r.title), _norm(r.artist))
        existing = best.get(key)
        if existing is None:
            best[key] = r
            order.append(key)
        else:
            existing_price = existing.price_value if existing.price_value is not None else float("inf")
            new_price = r.price_value if r.price_value is not None else float("inf")
            if new_price < existing_price:
                best[key] = r

    return [best[k] for k in order]


def get_store_list() -> list[dict]:
    return [
        {"key": key, "name": mod.STORE_NAME}
        for key, mod in _STORES.items()
    ]


def search_all(query: str, selected_stores: Optional[list[str]] = None) -> list[TrackResult]:
    keys = selected_stores or list(_STORES.keys())
    modules = [(k, _STORES[k]) for k in keys if k in _STORES]

    results: list[TrackResult] = []

    def _search(item):
        key, mod = item
        try:
            return mod.search(query)
        except Exception as e:
            print(f"Error searching {key}: {e}")
            return []

    with concurrent.futures.ThreadPoolExecutor(max_workers=len(modules)) as executor:
        for partial in executor.map(_search, modules):
            results.extend(partial)

    return _dedupe(results)
