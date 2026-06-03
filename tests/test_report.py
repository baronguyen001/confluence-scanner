from __future__ import annotations

import base64
import re

import pandas as pd

from confscan.backtest.engine import run_backtest
from confscan.backtest.metrics import Metrics
from confscan.backtest.report import (
    FoldReportRow,
    render_html_report,
    write_html_report,
)


def test_render_html_report_embeds_png_and_tables(tiny_ohlcv: pd.DataFrame) -> None:
    entry = pd.Series(False, index=tiny_ohlcv.index)
    exit_ = pd.Series(False, index=tiny_ohlcv.index)
    entry.iloc[0] = True
    exit_.iloc[3] = True
    result = run_backtest(tiny_ohlcv, entry, exit_, fee_bps=0, initial_capital=1000)
    metrics = Metrics.from_result(result)
    html = render_html_report(
        result,
        symbol="BTCUSDT",
        metrics=metrics,
        folds=(
            FoldReportRow(
                name="fold 1",
                start="2024-01-01",
                end="2024-01-02",
                total_return=result.total_return,
                sharpe=metrics.sharpe,
                max_drawdown=metrics.max_drawdown,
                n_trades=metrics.n_trades,
            ),
        ),
    )

    assert "BTCUSDT" in html
    assert "Total return" in html
    assert "fold 1" in html
    match = re.search(r"data:image/png;base64,([A-Za-z0-9+/=]+)", html)
    assert match is not None
    assert base64.b64decode(match.group(1)).startswith(b"\x89PNG\r\n\x1a\n")


def test_write_html_report(tmp_path, tiny_ohlcv: pd.DataFrame) -> None:
    entry = pd.Series([True] + [False] * (len(tiny_ohlcv) - 1), index=tiny_ohlcv.index)
    exit_ = pd.Series(False, index=tiny_ohlcv.index)
    result = run_backtest(tiny_ohlcv, entry, exit_, fee_bps=0)
    target = tmp_path / "report.html"

    from confscan.backtest.report import BacktestReportSection

    written = write_html_report(
        target,
        [
            BacktestReportSection(
                symbol="BTCUSDT", result=result, metrics=Metrics.from_result(result)
            )
        ],
    )

    assert written == target
    assert "data:image/png;base64" in target.read_text(encoding="utf-8")
