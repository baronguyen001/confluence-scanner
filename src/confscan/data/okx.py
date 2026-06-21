"""OKX public market data fetchers.

A third, independent funding-rate source. Like :mod:`confscan.data.bybit`, the
returned frame is normalized to the Binance-compatible shape (a single
``fundingRate`` float column on a UTC ``DatetimeIndex``), so the funding
sub-score stays source-agnostic.
"""

from __future__ import annotations

import pandas as pd

from confscan.data.http import get_json

OKX_BASE = "https://www.okx.com"


def to_inst_id(symbol: str) -> str:
    """Map a Binance-style ``BTCUSDT`` symbol to an OKX swap ``BTC-USDT-SWAP``."""
    symbol = symbol.upper()
    for quote in ("USDT", "USDC", "USD"):
        if symbol.endswith(quote) and len(symbol) > len(quote):
            return f"{symbol[: -len(quote)]}-{quote}-SWAP"
    return symbol


def _rows_to_frame(rows: list) -> pd.DataFrame:
    """Normalize OKX funding rows to the Binance-compatible funding frame."""
    if not rows:
        return pd.DataFrame(columns=["fundingRate"])
    df = pd.DataFrame(rows)
    if "fundingRate" not in df:
        return pd.DataFrame(columns=["fundingRate"])
    df["fundingRate"] = pd.to_numeric(df["fundingRate"], errors="coerce")
    df = df.dropna(subset=["fundingRate"])
    if "fundingTime" in df:
        ts = pd.to_numeric(df["fundingTime"], errors="coerce")
        df.index = pd.to_datetime(ts, unit="ms", utc=True)
        df = df.sort_index()
    return df[["fundingRate"]]


def funding_rate(symbol: str, *, limit: int = 100) -> pd.DataFrame:
    """Fetch recent funding rates from OKX, normalized to ``['fundingRate']``.

    Returns an empty frame on any failure so callers can fall back gracefully.
    OKX caps ``limit`` at 100 for this endpoint.
    """
    try:
        payload = get_json(
            f"{OKX_BASE}/api/v5/public/funding-rate-history",
            params={"instId": to_inst_id(symbol), "limit": min(max(int(limit), 1), 100)},
        )
    except Exception:
        return pd.DataFrame(columns=["fundingRate"])
    if not isinstance(payload, dict) or str(payload.get("code", "0")) not in ("0", "None"):
        return pd.DataFrame(columns=["fundingRate"])
    rows = payload.get("data")
    if not isinstance(rows, list):
        return pd.DataFrame(columns=["fundingRate"])
    return _rows_to_frame(rows)
