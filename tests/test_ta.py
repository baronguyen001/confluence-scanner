from __future__ import annotations

import pandas as pd

from confscan.signals.ta import (
    adx,
    atr,
    bollinger_bands,
    detect_cross,
    ema,
    ema_cross_signal,
    macd,
    rsi,
)


def test_ema_matches_pandas() -> None:
    series = pd.Series([1, 2, 3, 4], dtype=float)
    pd.testing.assert_series_equal(ema(series, 3), series.ewm(span=3, adjust=False).mean())


def test_detect_cross_vectorized() -> None:
    fast = pd.Series([1, 1, 3, 2, 1], dtype=float)
    slow = pd.Series([2, 2, 2, 2, 2], dtype=float)
    assert detect_cross(fast, slow).tolist() == [0, 0, 1, 0, -1]


def test_ema_cross_signal_uses_last_closed_bar(sample_ohlcv: pd.DataFrame) -> None:
    df = sample_ohlcv.tail(120).copy()
    closed = ema_cross_signal(df, fast=12, slow=26, trend=50, use_forming_bar=False)
    forming = ema_cross_signal(df, fast=12, slow=26, trend=50, use_forming_bar=True)
    assert closed["valid"] is True
    assert closed["signal_bar_idx"] == -2
    assert forming["signal_bar_idx"] == -1
    assert closed["entry_time"] == pd.Timestamp(df.index[-1]).isoformat()


def test_textbook_indicators_shape(sample_ohlcv: pd.DataFrame) -> None:
    close = sample_ohlcv["close"]
    macd_line, signal_line, hist = macd(close)
    lower, middle, upper = bollinger_bands(close)
    assert len(rsi(close)) == len(close)
    assert len(macd_line) == len(signal_line) == len(hist) == len(close)
    assert (upper.dropna() >= middle.dropna()).all()
    assert (middle.dropna() >= lower.dropna()).all()
    assert atr(sample_ohlcv).dropna().gt(0).all()
    adx_values = adx(sample_ohlcv).dropna()
    assert len(adx_values) > 0
    assert adx_values.between(0, 100).all()


def test_atr_uses_true_range(tiny_ohlcv: pd.DataFrame) -> None:
    values = atr(tiny_ohlcv, period=3)
    assert round(float(values.iloc[2]), 6) == 2.555556


def test_adx_returns_trend_strength(sample_ohlcv: pd.DataFrame) -> None:
    values = adx(sample_ohlcv, period=14).dropna()
    assert values.index.is_monotonic_increasing
    assert values.between(0, 100).all()
