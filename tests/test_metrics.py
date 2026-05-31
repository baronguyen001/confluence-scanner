from __future__ import annotations

import pandas as pd

from confscan.backtest.engine import run_backtest
from confscan.backtest.metrics import Metrics, periods_per_year


def test_periods_per_year() -> None:
    assert periods_per_year("4h") == 2190
    assert periods_per_year("1h") == 8760
    assert periods_per_year("1d") == 365


def test_metrics_from_returns() -> None:
    returns = pd.Series([0.0, 0.1, -0.05, 0.02])
    metrics = Metrics.from_returns(returns)
    assert metrics.max_drawdown < 0
    assert metrics.profit_factor > 0
    assert metrics.n_trades == 0


def test_metrics_from_result(tiny_ohlcv: pd.DataFrame) -> None:
    entry = pd.Series(False, index=tiny_ohlcv.index)
    exit_ = pd.Series(False, index=tiny_ohlcv.index)
    entry.iloc[0] = True
    exit_.iloc[2] = True
    metrics = Metrics.from_result(run_backtest(tiny_ohlcv, entry, exit_, fee_bps=0))
    assert metrics.n_trades == 1
    assert metrics.win_rate == 1
