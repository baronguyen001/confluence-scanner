"""Tests for the v0.5 generic indicators (stochastic, OBV, MFI)."""

from __future__ import annotations

import numpy as np
import pandas as pd

from confscan.signals.ta import mfi, obv, stochastic


def _ohlcv(n: int = 40) -> pd.DataFrame:
    idx = pd.date_range("2024-01-01", periods=n, freq="4h", tz="UTC")
    close = pd.Series(100 + np.sin(np.arange(n) / 3.0) * 5, index=idx)
    high = close + 1.0
    low = close - 1.0
    volume = pd.Series(np.arange(1, n + 1) * 10.0, index=idx)
    return pd.DataFrame({"open": close, "high": high, "low": low, "close": close, "volume": volume})


def test_stochastic_bounded_0_100() -> None:
    k, d = stochastic(_ohlcv())
    valid = k.dropna()
    assert (valid >= 0).all() and (valid <= 100).all()
    # %D is a smoothing of %K, so it has at least as many NaNs at the head
    assert d.isna().sum() >= k.isna().sum()


def test_obv_is_cumulative_signed_volume() -> None:
    df = pd.DataFrame(
        {
            "open": [1, 1, 1, 1],
            "high": [1, 1, 1, 1],
            "low": [1, 1, 1, 1],
            "close": [10.0, 11.0, 10.0, 12.0],  # up, down, up
            "volume": [100.0, 200.0, 50.0, 75.0],
        }
    )
    result = obv(df)
    # first diff is 0 -> sign 0; then +200, -50, +75 -> cumulative 0,200,150,225
    assert list(result) == [0.0, 200.0, 150.0, 225.0]


def test_mfi_bounded_0_100() -> None:
    valid = mfi(_ohlcv()).dropna()
    assert (valid >= 0).all() and (valid <= 100).all()


def test_indicators_preserve_index() -> None:
    df = _ohlcv()
    assert obv(df).index.equals(df.index)
    assert mfi(df).index.equals(df.index)
    k, _ = stochastic(df)
    assert k.index.equals(df.index)
