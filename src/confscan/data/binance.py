"""Binance public market data fetchers."""

from __future__ import annotations

import re
import time
from datetime import UTC, datetime

import pandas as pd

from confscan.data.http import get_json

BINANCE_SPOT = "https://api.binance.com"
BINANCE_FAPI = "https://fapi.binance.com"

_INTERVAL_SECONDS = {
    "1m": 60,
    "5m": 300,
    "15m": 900,
    "1h": 3600,
    "2h": 7200,
    "4h": 14400,
    "1d": 86400,
}


def _lookback_to_ms(lookback: str) -> int:
    match = re.fullmatch(r"(\d+)([dhm])", lookback.strip().lower())
    if not match:
        raise ValueError("lookback must look like '90d', '24h', or '30m'")
    value = int(match.group(1))
    unit = match.group(2)
    seconds = {"d": 86400, "h": 3600, "m": 60}[unit] * value
    return int(seconds * 1000)


def _klines_to_frame(data: list) -> pd.DataFrame:
    if not data:
        return pd.DataFrame(columns=["open", "high", "low", "close", "volume"])
    cols = [
        "open_time",
        "open",
        "high",
        "low",
        "close",
        "volume",
        "close_time",
        "quote_volume",
        "trades",
        "taker_base_volume",
        "taker_quote_volume",
        "ignore",
    ]
    df = pd.DataFrame(data, columns=cols)
    for col in ("open", "high", "low", "close", "volume"):
        df[col] = df[col].astype(float)
    df["open_time"] = pd.to_datetime(df["open_time"], unit="ms", utc=True)
    df = df.set_index("open_time").sort_index()
    return df[["open", "high", "low", "close", "volume"]]


def klines(
    symbol: str,
    interval: str = "4h",
    *,
    limit: int = 500,
    lookback: str | None = None,
    start_ms: int | None = None,
    end_ms: int | None = None,
) -> pd.DataFrame:
    """Fetch OHLCV with a UTC DatetimeIndex. Returns an empty frame on failure."""

    symbol = symbol.upper()
    endpoint = f"{BINANCE_SPOT}/api/v3/klines"
    interval_seconds = _INTERVAL_SECONDS.get(interval, 14400)

    if lookback:
        end_ms = end_ms or int(datetime.now(UTC).timestamp() * 1000)
        start_ms = end_ms - _lookback_to_ms(lookback)

    if start_ms is None:
        try:
            data = get_json(
                endpoint,
                params={"symbol": symbol, "interval": interval, "limit": min(limit, 1000)},
            )
            return _klines_to_frame(data)
        except Exception:
            return pd.DataFrame(columns=["open", "high", "low", "close", "volume"])

    all_rows: list = []
    cursor = start_ms
    final_ms = end_ms or int(datetime.now(UTC).timestamp() * 1000)
    max_pages = max(1, min(100, (limit + 1499) // 1500 if limit else 100))
    for _ in range(max_pages):
        params = {
            "symbol": symbol,
            "interval": interval,
            "limit": 1500,
            "startTime": cursor,
            "endTime": final_ms,
        }
        try:
            chunk = get_json(endpoint, params=params)
        except Exception:
            break
        if not chunk:
            break
        all_rows.extend(chunk)
        next_open = int(chunk[-1][0]) + interval_seconds * 1000
        if next_open > final_ms or next_open <= cursor:
            break
        cursor = next_open
        time.sleep(0.05)

    if not all_rows:
        return pd.DataFrame(columns=["open", "high", "low", "close", "volume"])
    seen: set[int] = set()
    dedup = []
    for row in all_rows:
        open_time = int(row[0])
        if open_time not in seen:
            seen.add(open_time)
            dedup.append(row)
    dedup.sort(key=lambda r: int(r[0]))
    if limit and len(dedup) > limit:
        dedup = dedup[-limit:]
    return _klines_to_frame(dedup)


def funding_rate(symbol: str, *, limit: int = 100) -> pd.DataFrame:
    symbol = symbol.upper()
    try:
        data = get_json(
            f"{BINANCE_FAPI}/fapi/v1/fundingRate",
            params={"symbol": symbol, "limit": limit},
        )
    except Exception:
        try:
            item = get_json(f"{BINANCE_FAPI}/fapi/v1/premiumIndex", params={"symbol": symbol})
            data = [{"fundingTime": item.get("time"), "fundingRate": item.get("lastFundingRate")}]
        except Exception:
            data = []
    if not data:
        return pd.DataFrame(columns=["fundingRate"])
    df = pd.DataFrame(data)
    df["fundingRate"] = df["fundingRate"].astype(float)
    time_col = "fundingTime" if "fundingTime" in df else "time"
    if time_col in df:
        df.index = pd.to_datetime(df[time_col], unit="ms", utc=True)
    return df[["fundingRate"]]


def open_interest(symbol: str, *, period: str = "1d", limit: int = 8) -> pd.DataFrame:
    symbol = symbol.upper()
    try:
        data = get_json(
            f"{BINANCE_FAPI}/futures/data/openInterestHist",
            params={"symbol": symbol, "period": period, "limit": limit},
        )
    except Exception:
        return pd.DataFrame()
    if not data:
        return pd.DataFrame()
    df = pd.DataFrame(data)
    for col in ("sumOpenInterest", "sumOpenInterestValue"):
        if col in df:
            df[col] = df[col].astype(float)
    if "timestamp" in df:
        df.index = pd.to_datetime(df["timestamp"], unit="ms", utc=True)
    return df


def long_short_ratio(symbol: str, *, period: str = "1d", limit: int = 1) -> float | None:
    symbol = symbol.upper()
    try:
        data = get_json(
            f"{BINANCE_FAPI}/futures/data/topLongShortAccountRatio",
            params={"symbol": symbol, "period": period, "limit": limit},
        )
    except Exception:
        return None
    if not data:
        return None
    try:
        return float(data[-1]["longShortRatio"])
    except (KeyError, TypeError, ValueError):
        return None
