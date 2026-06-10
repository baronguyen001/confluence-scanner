"""Generic market-regime classification for per-regime backtest reporting.

Each bar is labelled ``bull``, ``bear``, or ``chop`` from a simple, parameter-light
trend/volatility rule, so backtest metrics can be sliced by regime. The rule is
deliberately generic (a trend EMA slope compared against a volatility-scaled
threshold) and is **not** a tuned production filter.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from confscan.backtest.metrics import Metrics
from confscan.signals.ta import ema

REGIMES = ("bull", "bear", "chop")


def classify_regimes(
    df: pd.DataFrame,
    *,
    trend: int = 100,
    vol_window: int = 20,
) -> pd.Series:
    """Label each bar ``bull`` / ``bear`` / ``chop`` on the frame's index.

    The trend EMA's recent slope is normalized by the bar return volatility. When
    the normalized slope exceeds the volatility band the regime is trending
    (bull/bear by sign); otherwise it is chop. Generic defaults only.
    """

    index = df.index
    if df.empty or "close" not in df:
        return pd.Series([], index=index, dtype="object")

    close = df["close"].astype(float)
    trend_ema = ema(close, trend)
    # Per-bar slope of the trend line, expressed as a fractional change.
    slope = trend_ema.pct_change().fillna(0.0)
    # Volatility band: rolling std of bar returns acts as a generic noise floor.
    vol = close.pct_change().rolling(vol_window, min_periods=1).std().fillna(0.0)

    labels: list[str] = []
    for s, v in zip(slope.to_numpy(), vol.to_numpy(), strict=False):
        threshold = 0.25 * float(v)
        if s > threshold:
            labels.append("bull")
        elif s < -threshold:
            labels.append("bear")
        else:
            labels.append("chop")
    return pd.Series(labels, index=index, dtype="object")


@dataclass(frozen=True)
class RegimeMetrics:
    regime: str
    n_periods: int
    share: float
    metrics: Metrics


def metrics_by_regime(
    returns: pd.Series,
    regimes: pd.Series,
    *,
    freq: str = "4h",
) -> list[RegimeMetrics]:
    """Compute :class:`Metrics` for each regime slice of ``returns``.

    Returns one entry per regime in ``bull``, ``bear``, ``chop`` order, skipping
    regimes with no bars. ``returns`` and ``regimes`` are aligned on their index.
    """

    if returns.empty or regimes.empty:
        return []
    aligned = regimes.reindex(returns.index)
    total = int(aligned.notna().sum())
    out: list[RegimeMetrics] = []
    for regime in REGIMES:
        mask = aligned == regime
        n = int(mask.sum())
        if n == 0:
            continue
        slice_returns = returns[mask]
        out.append(
            RegimeMetrics(
                regime=regime,
                n_periods=n,
                share=(n / total) if total else 0.0,
                metrics=Metrics.from_returns(slice_returns, freq=freq),
            )
        )
    return out
