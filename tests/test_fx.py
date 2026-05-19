from __future__ import annotations

import pytest

import fx


class FakeResponse:
    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code

    @property
    def ok(self):
        return 200 <= self.status_code < 300

    def json(self):
        return self._payload


@pytest.fixture(autouse=True)
def reset_fx_cache():
    fx._rates_per_eur.clear()
    fx._rates_per_eur["EUR"] = 1.0
    fx._fetched_at = 0.0
    yield


def test_eur_passes_through_without_network(monkeypatch):
    def explode(*a, **kw):
        raise AssertionError("convert_to_eur(EUR) must not hit the network")
    monkeypatch.setattr(fx.requests, "get", explode)

    assert fx.convert_to_eur(1.29, "EUR") == 1.29
    assert fx.convert_to_eur(2.50, "eur") == 2.50  # case-insensitive


def test_converts_usd_using_fetched_rate(monkeypatch):
    monkeypatch.setattr(
        fx.requests, "get",
        lambda *a, **kw: FakeResponse({"rates": {"USD": 1.10}}),
    )

    result = fx.convert_to_eur(2.20, "USD")
    assert result == pytest.approx(2.0)


def test_converts_gbp_when_rate_present(monkeypatch):
    monkeypatch.setattr(
        fx.requests, "get",
        lambda *a, **kw: FakeResponse({"rates": {"USD": 1.10, "GBP": 0.85}}),
    )

    result = fx.convert_to_eur(1.70, "GBP")
    assert result == pytest.approx(2.0)


def test_returns_none_for_unknown_currency(monkeypatch):
    monkeypatch.setattr(
        fx.requests, "get",
        lambda *a, **kw: FakeResponse({"rates": {"USD": 1.10}}),
    )

    assert fx.convert_to_eur(1.0, "XYZ") is None


def test_returns_none_when_refresh_fails(monkeypatch):
    monkeypatch.setattr(
        fx.requests, "get",
        lambda *a, **kw: FakeResponse({}, status_code=503),
    )

    # cache is empty (only EUR), USD lookup should yield None
    assert fx.convert_to_eur(1.0, "USD") is None


def test_returns_none_when_request_raises(monkeypatch):
    def boom(*a, **kw):
        raise RuntimeError("network down")
    monkeypatch.setattr(fx.requests, "get", boom)

    assert fx.convert_to_eur(1.0, "USD") is None


def test_zero_or_none_value_returns_none_or_zero(monkeypatch):
    monkeypatch.setattr(
        fx.requests, "get",
        lambda *a, **kw: FakeResponse({"rates": {"USD": 1.10}}),
    )

    assert fx.convert_to_eur(None, "USD") is None
    assert fx.convert_to_eur(0, "USD") == 0.0


def test_uses_cache_within_ttl(monkeypatch):
    calls = {"n": 0}

    def counting_get(*a, **kw):
        calls["n"] += 1
        return FakeResponse({"rates": {"USD": 1.10}})

    monkeypatch.setattr(fx.requests, "get", counting_get)

    fx.convert_to_eur(1.0, "USD")
    fx.convert_to_eur(2.0, "USD")
    fx.convert_to_eur(3.0, "USD")

    assert calls["n"] == 1
