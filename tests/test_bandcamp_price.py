from __future__ import annotations

import html
import json

from stores.bandcamp import _parse_track_price


def _page(current: dict, currency: str = "USD") -> str:
    """Build a minimal track page: Bandcamp stores the price as an HTML-escaped
    JSON blob in data-tralbum and the currency in a separate attribute."""
    blob = html.escape(json.dumps({"current": current}))
    parts = [f'<script data-tralbum="{blob}"></script>']
    if currency is not None:
        parts.append(f'<script data-band-currency="{currency}"></script>')
    return "".join(parts)


def test_name_your_price_with_minimum_shows_the_floor():
    page = _page({"is_set_price": None, "set_price": 1.5, "minimum_price": 1.5})
    assert _parse_track_price(page) == ("ab 1.50 USD", 1.5, "USD")


def test_fixed_price_uses_set_price():
    page = _page({"is_set_price": True, "set_price": 2.5, "minimum_price": 2.5})
    assert _parse_track_price(page) == ("2.50 USD", 2.5, "USD")


def test_name_your_price_without_minimum_is_unpriced():
    page = _page({"is_set_price": None, "set_price": 0, "minimum_price": 0})
    assert _parse_track_price(page) == ("Name Your Price", None, "USD")


def test_currency_comes_from_band_attribute():
    page = _page({"is_set_price": True, "set_price": 3.0, "minimum_price": 3.0}, currency="EUR")
    assert _parse_track_price(page) == ("3.00 EUR", 3.0, "EUR")


def test_missing_currency_falls_back_to_usd():
    page = _page({"is_set_price": True, "set_price": 3.0, "minimum_price": 3.0}, currency=None)
    assert _parse_track_price(page) == ("3.00 USD", 3.0, "USD")


def test_no_price_blob_returns_none():
    assert _parse_track_price("<html><body>no tralbum here</body></html>") is None
