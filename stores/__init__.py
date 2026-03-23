from __future__ import annotations

import concurrent.futures
from typing import Optional

from models import TrackResult
from stores import beatport, traxsource, juno, bandcamp, itunes

_STORES: dict[str, object] = {
    "beatport": beatport,
    "traxsource": traxsource,
    "juno": juno,
    "bandcamp": bandcamp,
    "itunes": itunes,
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
