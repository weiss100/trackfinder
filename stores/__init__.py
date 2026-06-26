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
