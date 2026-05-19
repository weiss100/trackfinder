"""In-process exchange-rate cache for converting store prices to EUR.

Pulls daily ECB rates from frankfurter.dev — no API key required. Rates are
refreshed lazily on demand (TTL: 6 hours) so the first conversion of the day
pays one ~200 ms network hit and every subsequent search is free. Failures
are swallowed; callers get None and the UI falls back to showing the
original currency only.
"""
from __future__ import annotations

import threading
import time
from typing import Optional

import requests

_API = "https://api.frankfurter.dev/v1/latest?base=EUR&symbols=USD,GBP,CHF,JPY,AUD,CAD"
_TTL_SECONDS = 6 * 3600

_lock = threading.Lock()
_rates_per_eur: dict[str, float] = {"EUR": 1.0}
_fetched_at: float = 0.0


def _refresh() -> None:
    global _fetched_at
    try:
        resp = requests.get(_API, timeout=5)
        if not resp.ok:
            return
        rates = resp.json().get("rates") or {}
        new_table = {"EUR": 1.0}
        for code, rate in rates.items():
            try:
                rate_f = float(rate)
            except (TypeError, ValueError):
                continue
            if rate_f > 0:
                new_table[code.upper()] = rate_f
        with _lock:
            _rates_per_eur.clear()
            _rates_per_eur.update(new_table)
            _fetched_at = time.time()
    except Exception as e:
        print(f"FX refresh error: {e}")


def convert_to_eur(value: float, currency: str) -> Optional[float]:
    """Convert *value* in *currency* to EUR. Returns None if unsupported/unknown."""
    if value is None:
        return None
    code = (currency or "").upper()
    if code == "EUR":
        return float(value)

    with _lock:
        is_stale = (time.time() - _fetched_at) > _TTL_SECONDS
    if is_stale:
        _refresh()

    with _lock:
        rate = _rates_per_eur.get(code)

    if not rate:
        return None
    return float(value) / rate
