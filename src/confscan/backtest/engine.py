"""Signal-driven long-only backtest engine."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import pandas as pd

if TYPE_CHECKING:
    from confscan.backtest.metrics import Metrics


@dataclass
class Trade:
    entry_ts: pd.Timestamp
    exit_ts: pd.Timestamp
    side: str
    entry_price: float
    exit_price: float
    pnl: float
    fees: float
    reason: str


@dataclass
class BacktestResult:
    equity_curve: pd.Series
    trades: list[Trade]
    returns: pd.Series
    buy_hold: float

    @property
    def total_return(self) -> float:
        if self.equity_curve.empty:
            return 0.0
        start = float(self.equity_curve.iloc[0])
        end = float(self.equity_curve.iloc[-1])
        return (end / start - 1.0) if start else 0.0

    @property
    def metrics(self) -> Metrics:
        from confscan.backtest.metrics import Metrics

        return Metrics.from_result(self)


def _aligned_bool(signal: pd.Series, index: pd.Index) -> pd.Series:
    return signal.reindex(index).fillna(False).astype(bool)


def run_backtest(
    df: pd.DataFrame,
    entry_signal: pd.Series,
    exit_signal: pd.Series,
    *,
    fee_bps: float = 10.0,
    initial_capital: float = 10_000.0,
    stop_loss_pct: float | None = None,
) -> BacktestResult:
    """Long-only replay using caller-supplied entry and exit signals."""

    if df.empty:
        empty = pd.Series(dtype=float)
        return BacktestResult(empty, [], empty, 0.0)
    required = {"open", "high", "low", "close"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"df missing columns: {sorted(missing)}")

    data = df.sort_index()
    entries = _aligned_bool(entry_signal, data.index)
    exits = _aligned_bool(exit_signal, data.index)
    fee_rate = fee_bps / 10_000.0

    cash = float(initial_capital)
    shares = 0.0
    in_position = False
    pending_entry = False
    pending_exit_reason: str | None = None
    entry_price = 0.0
    entry_ts = pd.Timestamp(data.index[0])
    entry_equity = cash
    entry_fee = 0.0
    stop_price: float | None = None
    trades: list[Trade] = []
    equity_values: list[float] = []

    def close_position(i: int, price: float, reason: str) -> None:
        nonlocal \
            cash, \
            shares, \
            in_position, \
            entry_price, \
            entry_ts, \
            entry_equity, \
            entry_fee, \
            stop_price
        gross = shares * price
        exit_fee = gross * fee_rate
        cash = gross - exit_fee
        pnl = cash - entry_equity
        trades.append(
            Trade(
                entry_ts=entry_ts,
                exit_ts=pd.Timestamp(data.index[i]),
                side="long",
                entry_price=entry_price,
                exit_price=float(price),
                pnl=float(pnl),
                fees=float(entry_fee + exit_fee),
                reason=reason,
            )
        )
        shares = 0.0
        in_position = False
        stop_price = None

    for i, (_, row) in enumerate(data.iterrows()):
        if pending_exit_reason and in_position:
            open_price = float(row["open"])
            close_position(i, open_price, pending_exit_reason)
            pending_exit_reason = None

        if pending_entry and not in_position:
            open_price = float(row["open"])
            if open_price > 0:
                entry_equity = cash
                entry_fee = cash * fee_rate
                shares = (cash - entry_fee) / open_price
                entry_price = open_price
                entry_ts = pd.Timestamp(data.index[i])
                in_position = True
                if stop_loss_pct is not None:
                    stop_price = entry_price * (1.0 + stop_loss_pct)
            pending_entry = False

        if in_position and stop_price is not None and float(row["low"]) <= stop_price:
            close_position(i, stop_price, "stop_loss")
            pending_exit_reason = None

        mark = shares * float(row["close"]) if in_position else cash
        equity_values.append(float(mark))

        if in_position and bool(exits.iloc[i]) and i + 1 < len(data):
            pending_exit_reason = "exit_signal"
        elif not in_position and bool(entries.iloc[i]) and i + 1 < len(data):
            pending_entry = True

    if in_position:
        close_position(len(data) - 1, float(data["close"].iloc[-1]), "end")
        equity_values[-1] = cash

    equity_curve = pd.Series(equity_values, index=data.index, name="equity")
    returns = equity_curve.pct_change().fillna(0.0)
    first_close = float(data["close"].iloc[0])
    last_close = float(data["close"].iloc[-1])
    buy_hold = (last_close / first_close - 1.0) if first_close else 0.0
    return BacktestResult(equity_curve, trades, returns, float(buy_hold))
