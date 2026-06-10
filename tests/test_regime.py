from __future__ import annotations

import pandas as pd

from confscan.backtest.engine import run_backtest
from confscan.backtest.regime import (
    REGIMES,
    classify_regimes,
    metrics_by_regime,
)


def _trending_frame(direction: int, periods: int = 160) -> pd.DataFrame:
    index = pd.date_range("2024-01-01", periods=periods, freq="4h", tz="UTC")
    closes = [100.0 + direction * i for i in range(periods)]
    return pd.DataFrame(
        {
            "open": closes,
            "high": [c + 1 for c in closes],
            "low": [c - 1 for c in closes],
            "close": closes,
            "volume": [10] * periods,
        },
        index=index,
    )


def test_classify_regimes_labels_and_index() -> None:
    df = _trending_frame(direction=1)
    labels = classify_regimes(df, trend=20)
    assert len(labels) == len(df)
    assert set(labels.unique()).issubset(set(REGIMES))


def test_classify_regimes_uptrend_is_bull() -> None:
    df = _trending_frame(direction=1)
    labels = classify_regimes(df, trend=20)
    # The dominant regime of a clean uptrend should be bull.
    assert labels.value_counts().idxmax() == "bull"


def test_classify_regimes_downtrend_is_bear() -> None:
    df = _trending_frame(direction=-1, periods=120)
    labels = classify_regimes(df, trend=20)
    assert labels.value_counts().idxmax() == "bear"


def test_classify_regimes_flat_is_chop() -> None:
    index = pd.date_range("2024-01-01", periods=80, freq="4h", tz="UTC")
    flat = pd.DataFrame(
        {
            "open": [100.0] * 80,
            "high": [100.5] * 80,
            "low": [99.5] * 80,
            "close": [100.0] * 80,
            "volume": [10] * 80,
        },
        index=index,
    )
    labels = classify_regimes(flat, trend=20)
    assert (labels == "chop").all()


def test_classify_regimes_empty() -> None:
    empty = pd.DataFrame(columns=["open", "high", "low", "close", "volume"])
    assert classify_regimes(empty).empty


def test_metrics_by_regime_partitions_returns() -> None:
    df = _trending_frame(direction=1)
    entry = pd.Series(False, index=df.index)
    exit_ = pd.Series(False, index=df.index)
    entry.iloc[0] = True
    exit_.iloc[-2] = True
    result = run_backtest(df, entry, exit_, fee_bps=0)
    regimes = classify_regimes(df, trend=20)
    breakdown = metrics_by_regime(result.returns, regimes, freq="4h")

    assert breakdown, "expected at least one regime slice"
    # Reported regimes follow bull/bear/chop ordering.
    order = [rm.regime for rm in breakdown]
    assert order == [r for r in REGIMES if r in order]
    # Bar counts across regimes equal the labelled total.
    assert sum(rm.n_periods for rm in breakdown) == int(regimes.notna().sum())
    # Shares sum to ~1 across present regimes.
    assert abs(sum(rm.share for rm in breakdown) - 1.0) < 1e-9


def test_metrics_by_regime_empty() -> None:
    empty = pd.Series([], dtype=float)
    assert metrics_by_regime(empty, empty) == []
