from __future__ import annotations

import pandas as pd

from confscan.backtest.engine import run_backtest


def test_run_backtest_enters_next_open_and_exits_next_open(tiny_ohlcv: pd.DataFrame) -> None:
    entry = pd.Series(False, index=tiny_ohlcv.index)
    exit_ = pd.Series(False, index=tiny_ohlcv.index)
    entry.iloc[0] = True
    exit_.iloc[3] = True
    result = run_backtest(tiny_ohlcv, entry, exit_, fee_bps=0, initial_capital=1000)
    assert len(result.trades) == 1
    trade = result.trades[0]
    assert trade.entry_ts == tiny_ohlcv.index[1]
    assert trade.exit_ts == tiny_ohlcv.index[4]
    assert trade.entry_price == 101
    assert trade.exit_price == 104
    assert round(result.total_return, 6) == round(104 / 101 - 1, 6)


def test_run_backtest_stop_loss(tiny_ohlcv: pd.DataFrame) -> None:
    entry = pd.Series(False, index=tiny_ohlcv.index)
    exit_ = pd.Series(False, index=tiny_ohlcv.index)
    entry.iloc[0] = True
    df = tiny_ohlcv.copy()
    df.iloc[2, df.columns.get_loc("low")] = 90
    generic_stop = -1 / 20
    result = run_backtest(
        df, entry, exit_, fee_bps=0, initial_capital=1000, stop_loss_pct=generic_stop
    )
    assert result.trades[0].reason == "stop_loss"
