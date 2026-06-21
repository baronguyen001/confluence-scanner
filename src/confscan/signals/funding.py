"""Funding-rate helpers.

The funding sub-score can read from more than one public perpetuals venue. The
source is selectable via config (``data.funding_source = binance | bybit | both``)
and defaults to ``binance`` so shipped behavior is unchanged. ``both`` averages the
two source frames after aligning them, which smooths over a single venue's outages.
"""

from __future__ import annotations

import pandas as pd

from confscan.data import bybit, okx
from confscan.data.binance import funding_rate

FUNDING_SOURCES = ("binance", "bybit", "okx", "both")

__all__ = [
    "FUNDING_SOURCES",
    "funding_rate",
    "funding_percentile",
    "funding_frame",
    "funding_score",
]


def funding_percentile(rates: pd.Series, current: float) -> float:
    """Return the empirical percentile of `current` inside `rates` on 0..1."""

    clean = rates.dropna().astype(float)
    if clean.empty:
        return 0.5
    return float((clean <= current).mean())


def funding_frame(symbol: str, *, source: str = "binance", limit: int = 100) -> pd.DataFrame:
    """Return a ``['fundingRate']`` frame for the requested source.

    ``both`` concatenates the Binance and Bybit histories and averages overlapping
    timestamps, falling back to whichever source returned data when one is empty.
    """

    source = (source or "binance").strip().lower()
    if source == "bybit":
        return bybit.funding_rate(symbol, limit=limit)
    if source == "okx":
        return okx.funding_rate(symbol, limit=limit)
    if source == "both":
        a = funding_rate(symbol, limit=limit)
        b = bybit.funding_rate(symbol, limit=limit)
        if a.empty:
            return b
        if b.empty:
            return a
        merged = pd.concat([a["fundingRate"], b["fundingRate"]])
        combined = merged.groupby(level=0).mean().sort_index().to_frame("fundingRate")
        return combined
    return funding_rate(symbol, limit=limit)


def funding_score(symbol: str, *, source: str = "binance") -> float:
    """Return a 0..1 generic funding sub-score.

    Lower funding is treated as less crowded for a long-only research workflow.
    This is intentionally a generic helper, not a production entry rule.
    """

    df = funding_frame(symbol, source=source, limit=100)
    if df.empty or "fundingRate" not in df:
        return 0.5
    current = float(df["fundingRate"].iloc[-1])
    pct = funding_percentile(df["fundingRate"], current)
    return max(0.0, min(1.0, 1.0 - pct))
