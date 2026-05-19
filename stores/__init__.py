from __future__ import annotations

import concurrent.futures
from typing import Optional

from models import TrackResult
from stores import beatport, traxsource, juno, itunes, amazon_music

# Bandcamp is intentionally excluded: its search pages are served behind a
# Fastly bot-management challenge that requires a real JS runtime to solve.
# Re-add only if we ever wire up a headless browser.

_STORES: dict[str, object] = {
    "beatport": beatport,
    "traxsource": traxsource,
    "juno": juno,
    "itunes": itunes,
    "amazon": amazon_music,
}


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

    return results
