from __future__ import annotations

import pandas as pd

from confscan.backtest.engine import run_backtest
from confscan.backtest.montecarlo import run_monte_carlo
from confscan.backtest.report import BacktestReportSection, render_html_document


def _two_trade_result(tiny_ohlcv: pd.DataFrame):
    entry = pd.Series(False, index=tiny_ohlcv.index)
    exit_ = pd.Series(False, index=tiny_ohlcv.index)
    entry.iloc[0] = True
    exit_.iloc[2] = True
    entry.iloc[4] = True
    exit_.iloc[6] = True
    return run_backtest(tiny_ohlcv, entry, exit_, fee_bps=0, initial_capital=1000)


def test_monte_carlo_is_deterministic_with_seed(tiny_ohlcv: pd.DataFrame) -> None:
    result = _two_trade_result(tiny_ohlcv)

    a = run_monte_carlo(result, simulations=50, seed=7)
    b = run_monte_carlo(result, simulations=50, seed=7)

    assert a == b
    assert a.simulations == 50
    assert [method.name for method in a.methods] == ["shuffle", "bootstrap"]


def test_monte_carlo_band_math_from_known_returns(tiny_ohlcv: pd.DataFrame) -> None:
    result = _two_trade_result(tiny_ohlcv)

    mc = run_monte_carlo(result, simulations=20, seed=1)
    shuffle = next(method for method in mc.methods if method.name == "shuffle")

    assert shuffle.final_return_low <= shuffle.final_return_median <= shuffle.final_return_high
    assert shuffle.max_drawdown_low <= shuffle.max_drawdown_median <= shuffle.max_drawdown_high
    assert shuffle.final_return_median > 0


def test_monte_carlo_surfaces_in_html_report(tiny_ohlcv: pd.DataFrame) -> None:
    result = _two_trade_result(tiny_ohlcv)
    mc = run_monte_carlo(result, simulations=10, seed=3)

    html = render_html_document(
        [
            BacktestReportSection(
                symbol="BTCUSDT",
                result=result,
                metrics=result.metrics,
                monte_carlo=mc,
            )
        ]
    )

    assert "Monte Carlo robustness" in html
    assert "bootstrap" in html
    assert "confidence band" in html
