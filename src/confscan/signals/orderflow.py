"""Generic public derivatives order-flow signal helpers.

The module uses free Binance futures market-data endpoints and returns neutral
fallbacks when a field is unavailable. It is intentionally a generic framework
layer; no production thresholds or tuned weights are shipped.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from confscan.data.binance import BINANCE_FAPI, long_short_ratio, open_interest
from confscan.data.http import get_json


@dataclass(frozen=True)
class OrderFlowComponents:
    open_interest: float | None
    long_short_ratio: float | None
    liquidations: float | None


def liquidations_frame(symbol: str, *, limit: int = 100) -> pd.DataFrame:
    """Fetch recent public liquidation orders from Binance futures.

    The returned frame has ``side``, ``price``, ``quantity``, and ``notional``
    columns on a UTC ``DatetimeIndex``. Empty frames signal unavailable data.
    """

    symbol = symbol.upper()
    try:
        rows = get_json(
            f"{BINANCE_FAPI}/fapi/v1/allForceOrders",
            params={
                "symbol": symbol,
                "autoCloseType": "LIQUIDATION",
                "limit": min(max(int(limit), 1), 1000),
            },
        )
    except Exception:
        return pd.DataFrame(columns=["side", "price", "quantity", "notional"])
    if not isinstance(rows, list) or not rows:
        return pd.DataFrame(columns=["side", "price", "quantity", "notional"])

    df = pd.DataFrame(rows)
    required = {"side", "price", "origQty"}
    if not required.issubset(df.columns):
        return pd.DataFrame(columns=["side", "price", "quantity", "notional"])
    df["price"] = pd.to_numeric(df["price"], errors="coerce")
    df["quantity"] = pd.to_numeric(df["origQty"], errors="coerce")
    df["notional"] = df["price"] * df["quantity"]
    df["side"] = df["side"].astype(str).str.upper()
    if "time" in df:
        df.index = pd.to_datetime(pd.to_numeric(df["time"], errors="coerce"), unit="ms", utc=True)
        df = df.sort_index()
    return df[["side", "price", "quantity", "notional"]].dropna(subset=["notional"])


def _open_interest_component(frame: pd.DataFrame) -> float | None:
    if frame.empty or "sumOpenInterest" not in frame:
        return None
    values = frame["sumOpenInterest"].dropna().astype(float)
    if values.empty:
        return None
    latest = float(values.iloc[-1])
    return float((values <= latest).mean())


def _long_short_component(value: float | None) -> float | None:
    if value is None or value <= 0:
        return None
    # Ratio of 1.0 maps to neutral 0.5; crowded long readings fade toward 0.
    return max(0.0, min(1.0, 1.0 / (1.0 + float(value))))


def _liquidation_component(frame: pd.DataFrame) -> float | None:
    if frame.empty or "notional" not in frame or "side" not in frame:
        return None
    totals = frame.groupby("side")["notional"].sum()
    long_liq = float(totals.get("SELL", 0.0))
    short_liq = float(totals.get("BUY", 0.0))
    total = long_liq + short_liq
    if total <= 0:
        return None
    return max(0.0, min(1.0, short_liq / total))


def orderflow_components(
    symbol: str, *, period: str = "1d", limit: int = 30
) -> OrderFlowComponents:
    """Return normalized 0..1 components from free public order-flow endpoints."""

    oi = _open_interest_component(open_interest(symbol, period=period, limit=limit))
    lsr = _long_short_component(long_short_ratio(symbol, period=period, limit=1))
    liq = _liquidation_component(liquidations_frame(symbol, limit=limit))
    return OrderFlowComponents(open_interest=oi, long_short_ratio=lsr, liquidations=liq)


def orderflow_score(symbol: str, *, period: str = "1d", limit: int = 30) -> float:
    """Return a generic 0..1 order-flow score.

    Available components are averaged equally. If all public endpoints are
    unavailable, the layer returns neutral 0.5 rather than inventing a signal.
    """

    components = orderflow_components(symbol, period=period, limit=limit)
    values = [
        value
        for value in (
            components.open_interest,
            components.long_short_ratio,
            components.liquidations,
        )
        if value is not None
    ]
    if not values:
        return 0.5
    return max(0.0, min(1.0, float(sum(values) / len(values))))
