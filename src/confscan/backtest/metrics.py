"""Backtest metrics."""

from __future__ import annotations

import math
import re
from dataclasses import dataclass

import pandas as pd


def periods_per_year(freq: str) -> float:
    freq = freq.strip().lower()
    if freq.endswith("min"):
        minutes = float(freq[:-3])
        return 365.0 * 24.0 * 60.0 / minutes
    match = re.fullmatch(r"(\d+)([mhd])", freq)
    if not match:
        return 365.0
    value = float(match.group(1))
    unit = match.group(2)
    if unit == "m":
        return 365.0 * 24.0 * 60.0 / value
    if unit == "h":
        return 365.0 * 24.0 / value
    return 365.0 / value


@dataclass
class Metrics:
    sharpe: float
    cagr: float
    max_drawdown: float
    profit_factor: float
    win_rate: float
    n_trades: int

    @classmethod
    def from_returns(cls, returns: pd.Series, *, freq: str = "4h") -> Metrics:
        clean = returns.fillna(0.0).astype(float)
        if clean.empty:
            return cls(0.0, 0.0, 0.0, 0.0, 0.0, 0)
        ppy = periods_per_year(freq)
        std = float(clean.std(ddof=0))
        sharpe = float(clean.mean() / std * math.sqrt(ppy)) if std else 0.0
        equity = (1.0 + clean).cumprod()
        total = float(equity.iloc[-1])
        years = max(len(clean) / ppy, 1 / ppy)
        cagr = total ** (1.0 / years) - 1.0 if total > 0 else -1.0
        peak = equity.cummax()
        max_dd = float(((equity - peak) / peak).min())
        gains = clean[clean > 0].sum()
        losses = clean[clean < 0].sum()
        profit_factor = float(gains / abs(losses)) if losses < 0 else float("inf")
        win_rate = float((clean > 0).mean())
        return cls(
            sharpe=sharpe,
            cagr=float(cagr),
            max_drawdown=max_dd,
            profit_factor=profit_factor,
            win_rate=win_rate,
            n_trades=0,
        )

    @classmethod
    def from_result(cls, result, *, freq: str = "4h") -> Metrics:
        metrics = cls.from_returns(result.returns, freq=freq)
        trade_pnls = [float(t.pnl) for t in result.trades]
        if trade_pnls:
            gains = sum(p for p in trade_pnls if p > 0)
            losses = sum(p for p in trade_pnls if p < 0)
            metrics.profit_factor = gains / abs(losses) if losses < 0 else float("inf")
            metrics.win_rate = sum(1 for p in trade_pnls if p > 0) / len(trade_pnls)
            metrics.n_trades = len(trade_pnls)
        return metrics
