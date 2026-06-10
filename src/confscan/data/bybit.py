"""Bybit public market data fetchers.

A second, independent funding-rate source. The returned frame is normalized to the
same shape that :mod:`confscan.signals.funding` consumes from Binance: a single
``fundingRate`` float column on a UTC ``DatetimeIndex``. This keeps the funding
sub-score source-agnostic so a caller can pick Binance, Bybit, or an aggregate of
both without changing downstream code.
"""

from __future__ import annotations

import pandas as pd

from confscan.data.http import get_json

BYBIT_BASE = "https://api.bybit.com"


def _rows_to_frame(rows: list) -> pd.DataFrame:
    """Normalize Bybit funding rows to the Binance-compatible funding frame."""

    if not rows:
        return pd.DataFrame(columns=["fundingRate"])
    df = pd.DataFrame(rows)
    if "fundingRate" not in df:
        return pd.DataFrame(columns=["fundingRate"])
    df["fundingRate"] = df["fundingRate"].astype(float)
    if "fundingRateTimestamp" in df:
        ts = pd.to_numeric(df["fundingRateTimestamp"], errors="coerce")
        df.index = pd.to_datetime(ts, unit="ms", utc=True)
        df = df.sort_index()
    return df[["fundingRate"]]


def funding_rate(symbol: str, *, limit: int = 100, category: str = "linear") -> pd.DataFrame:
    """Fetch recent funding rates from Bybit, normalized to ``['fundingRate']``.

    Returns an empty frame on any failure so callers can fall back gracefully.
    Bybit caps ``limit`` at 200 for this endpoint.
    """

    symbol = symbol.upper()
    try:
        payload = get_json(
            f"{BYBIT_BASE}/v5/market/funding/history",
            params={
                "category": category,
                "symbol": symbol,
                "limit": min(max(int(limit), 1), 200),
            },
        )
    except Exception:
        return pd.DataFrame(columns=["fundingRate"])
    if not isinstance(payload, dict) or payload.get("retCode") not in (0, None):
        return pd.DataFrame(columns=["fundingRate"])
    result = payload.get("result") or {}
    rows = result.get("list") if isinstance(result, dict) else None
    if not isinstance(rows, list):
        return pd.DataFrame(columns=["fundingRate"])
    return _rows_to_frame(rows)
