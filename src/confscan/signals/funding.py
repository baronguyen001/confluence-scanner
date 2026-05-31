"""Funding-rate helpers."""

from __future__ import annotations

import pandas as pd

from confscan.data.binance import funding_rate


def funding_percentile(rates: pd.Series, current: float) -> float:
    """Return the empirical percentile of `current` inside `rates` on 0..1."""

    clean = rates.dropna().astype(float)
    if clean.empty:
        return 0.5
    return float((clean <= current).mean())


def funding_score(symbol: str) -> float:
    """Return a 0..1 generic funding sub-score.

    Lower funding is treated as less crowded for a long-only research workflow.
    This is intentionally a generic helper, not a production entry rule.
    """

    df = funding_rate(symbol, limit=100)
    if df.empty or "fundingRate" not in df:
        return 0.5
    current = float(df["fundingRate"].iloc[-1])
    pct = funding_percentile(df["fundingRate"], current)
    return max(0.0, min(1.0, 1.0 - pct))
