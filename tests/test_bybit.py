from __future__ import annotations

import pandas as pd

from confscan.data import binance, bybit
from confscan.signals import funding

BYBIT_FIXTURE = {
    "retCode": 0,
    "retMsg": "OK",
    "result": {
        "category": "linear",
        "list": [
            {
                "symbol": "BTCUSDT",
                "fundingRate": "0.00012",
                "fundingRateTimestamp": "1704067200000",
            },
            {
                "symbol": "BTCUSDT",
                "fundingRate": "0.00008",
                "fundingRateTimestamp": "1704096000000",
            },
        ],
    },
}


def test_bybit_funding_rate_parse(monkeypatch) -> None:
    monkeypatch.setattr(bybit, "get_json", lambda *a, **k: BYBIT_FIXTURE)
    df = bybit.funding_rate("BTCUSDT")
    assert list(df.columns) == ["fundingRate"]
    assert df.index.tz is not None
    # Sorted by timestamp ascending, so the latest row is the smaller rate.
    assert float(df["fundingRate"].iloc[-1]) == 0.00008
    assert len(df) == 2


def test_bybit_funding_rate_handles_error(monkeypatch) -> None:
    def boom(*a, **k):
        raise RuntimeError("network down")

    monkeypatch.setattr(bybit, "get_json", boom)
    assert bybit.funding_rate("BTCUSDT").empty


def test_bybit_funding_rate_non_ok_retcode(monkeypatch) -> None:
    monkeypatch.setattr(bybit, "get_json", lambda *a, **k: {"retCode": 10001, "result": {}})
    assert bybit.funding_rate("BTCUSDT").empty


def test_funding_frame_source_selection(monkeypatch) -> None:
    binance_df = pd.DataFrame(
        {"fundingRate": [0.0002]},
        index=pd.to_datetime([1704067200000], unit="ms", utc=True),
    )
    monkeypatch.setattr(bybit, "get_json", lambda *a, **k: BYBIT_FIXTURE)
    monkeypatch.setattr(funding, "funding_rate", lambda *a, **k: binance_df)

    bybit_frame = funding.funding_frame("BTCUSDT", source="bybit")
    assert float(bybit_frame["fundingRate"].iloc[-1]) == 0.00008

    binance_frame = funding.funding_frame("BTCUSDT", source="binance")
    assert float(binance_frame["fundingRate"].iloc[-1]) == 0.0002


def test_funding_frame_both_averages_overlap(monkeypatch) -> None:
    ts = pd.to_datetime([1704067200000], unit="ms", utc=True)
    monkeypatch.setattr(
        funding,
        "funding_rate",
        lambda *a, **k: pd.DataFrame({"fundingRate": [0.0002]}, index=ts),
    )
    monkeypatch.setattr(
        funding.bybit,
        "funding_rate",
        lambda *a, **k: pd.DataFrame({"fundingRate": [0.0004]}, index=ts),
    )
    combined = funding.funding_frame("BTCUSDT", source="both")
    assert len(combined) == 1
    assert abs(float(combined["fundingRate"].iloc[0]) - 0.0003) < 1e-12


def test_funding_frame_both_falls_back_when_one_empty(monkeypatch) -> None:
    ts = pd.to_datetime([1704067200000], unit="ms", utc=True)
    monkeypatch.setattr(
        funding,
        "funding_rate",
        lambda *a, **k: pd.DataFrame(columns=["fundingRate"]),
    )
    monkeypatch.setattr(
        funding.bybit,
        "funding_rate",
        lambda *a, **k: pd.DataFrame({"fundingRate": [0.0004]}, index=ts),
    )
    combined = funding.funding_frame("BTCUSDT", source="both")
    assert float(combined["fundingRate"].iloc[-1]) == 0.0004


def test_funding_score_uses_source(monkeypatch) -> None:
    monkeypatch.setattr(bybit, "get_json", lambda *a, **k: BYBIT_FIXTURE)
    # No real Binance call should happen for source="bybit".
    monkeypatch.setattr(
        binance, "get_json", lambda *a, **k: (_ for _ in ()).throw(AssertionError("called"))
    )
    score = funding.funding_score("BTCUSDT", source="bybit")
    assert 0.0 <= score <= 1.0
