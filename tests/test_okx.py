"""Tests for the OKX funding-rate source (v0.5). Fixtured — no live calls."""

from __future__ import annotations

from confscan.data import okx
from confscan.signals import funding

OKX_FIXTURE = {
    "code": "0",
    "msg": "",
    "data": [
        {"instId": "BTC-USDT-SWAP", "fundingRate": "0.00012", "fundingTime": "1704067200000"},
        {"instId": "BTC-USDT-SWAP", "fundingRate": "0.00008", "fundingTime": "1704096000000"},
    ],
}


def test_to_inst_id_maps_symbol() -> None:
    assert okx.to_inst_id("BTCUSDT") == "BTC-USDT-SWAP"
    assert okx.to_inst_id("ethusdt") == "ETH-USDT-SWAP"
    assert okx.to_inst_id("BTCUSDC") == "BTC-USDC-SWAP"


def test_okx_funding_rate_parse(monkeypatch) -> None:
    monkeypatch.setattr(okx, "get_json", lambda *a, **k: OKX_FIXTURE)
    df = okx.funding_rate("BTCUSDT")
    assert list(df.columns) == ["fundingRate"]
    assert df.index.tz is not None
    assert float(df["fundingRate"].iloc[-1]) == 0.00008  # sorted ascending by time
    assert len(df) == 2


def test_okx_funding_rate_handles_error(monkeypatch) -> None:
    def boom(*a, **k):
        raise RuntimeError("network down")

    monkeypatch.setattr(okx, "get_json", boom)
    df = okx.funding_rate("BTCUSDT")
    assert df.empty
    assert list(df.columns) == ["fundingRate"]


def test_okx_bad_code_returns_empty(monkeypatch) -> None:
    monkeypatch.setattr(okx, "get_json", lambda *a, **k: {"code": "51000", "data": []})
    assert okx.funding_rate("BTCUSDT").empty


def test_funding_source_okx_selectable(monkeypatch) -> None:
    assert "okx" in funding.FUNDING_SOURCES
    monkeypatch.setattr(
        funding.okx, "funding_rate", lambda *a, **k: okx._rows_to_frame(OKX_FIXTURE["data"])
    )
    frame = funding.funding_frame("BTCUSDT", source="okx")
    assert list(frame.columns) == ["fundingRate"]
    assert len(frame) == 2
