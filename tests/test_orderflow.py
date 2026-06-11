from __future__ import annotations

import pandas as pd

from confscan.score.confluence import ConfluenceScorer
from confscan.signals import orderflow

LIQUIDATION_FIXTURE = [
    {
        "symbol": "BTCUSDT",
        "side": "BUY",
        "price": "100.0",
        "origQty": "2.0",
        "time": 1704067200000,
    },
    {
        "symbol": "BTCUSDT",
        "side": "SELL",
        "price": "100.0",
        "origQty": "1.0",
        "time": 1704070800000,
    },
]


def test_liquidations_frame_normalizes_public_response(monkeypatch) -> None:
    monkeypatch.setattr(orderflow, "get_json", lambda *a, **k: LIQUIDATION_FIXTURE)

    df = orderflow.liquidations_frame("BTCUSDT")

    assert list(df.columns) == ["side", "price", "quantity", "notional"]
    assert df.index.tz is not None
    assert float(df["notional"].sum()) == 300.0


def test_orderflow_score_averages_available_components(monkeypatch) -> None:
    oi = pd.DataFrame(
        {"sumOpenInterest": [100.0, 110.0, 120.0]},
        index=pd.date_range("2024-01-01", periods=3, freq="1d", tz="UTC"),
    )
    monkeypatch.setattr(orderflow, "open_interest", lambda *a, **k: oi)
    monkeypatch.setattr(orderflow, "long_short_ratio", lambda *a, **k: 1.0)
    monkeypatch.setattr(orderflow, "get_json", lambda *a, **k: LIQUIDATION_FIXTURE)

    score = orderflow.orderflow_score("BTCUSDT")

    assert round(score, 6) == round((1.0 + 0.5 + (200.0 / 300.0)) / 3.0, 6)


def test_orderflow_confluence_layer_is_zero_weight_by_default() -> None:
    result = ConfluenceScorer().score(
        "BTCUSDT",
        {"ta": 80, "fa": 60, "cex": 50, "onchain": 40, "orderflow": 100},
    )

    assert result.total == 62.0
    assert all(layer.name != "orderflow" for layer in result.layers)


def test_orderflow_confluence_layer_can_be_opted_in() -> None:
    result = ConfluenceScorer(
        weights={
            "ta": 0.35,
            "fa": 0.20,
            "cex": 0.20,
            "onchain": 0.15,
            "orderflow": 0.10,
        }
    ).score(
        "BTCUSDT",
        {"ta": 80, "fa": 60, "cex": 50, "onchain": 40, "orderflow": 100},
    )

    layers = {layer.name: layer for layer in result.layers}
    assert layers["orderflow"].weight == 0.1
    assert result.total == 66.0
