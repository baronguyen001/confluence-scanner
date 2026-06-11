"""HTML report rendering for backtest results."""

from __future__ import annotations

import base64
import html
import math
import struct
import zlib
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from confscan.backtest.engine import BacktestResult
from confscan.backtest.metrics import Metrics
from confscan.backtest.montecarlo import MonteCarloResult

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


@dataclass(frozen=True)
class FoldReportRow:
    name: str
    start: str
    end: str
    total_return: float
    sharpe: float
    max_drawdown: float
    n_trades: int


@dataclass(frozen=True)
class RegimeReportRow:
    regime: str
    n_periods: int
    share: float
    sharpe: float
    cagr: float
    max_drawdown: float
    win_rate: float


@dataclass(frozen=True)
class BacktestReportSection:
    symbol: str
    result: BacktestResult
    metrics: Metrics
    folds: tuple[FoldReportRow, ...] = ()
    regimes: tuple[RegimeReportRow, ...] = ()
    monte_carlo: MonteCarloResult | None = None


def _png_chunk(name: bytes, data: bytes) -> bytes:
    return (
        struct.pack(">I", len(data))
        + name
        + data
        + struct.pack(">I", zlib.crc32(name + data) & 0xFFFFFFFF)
    )


def _encode_png(width: int, height: int, pixels: bytearray) -> bytes:
    raw = bytearray()
    row_len = width * 3
    for y in range(height):
        raw.append(0)
        start = y * row_len
        raw.extend(pixels[start : start + row_len])
    header = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    return (
        PNG_SIGNATURE
        + _png_chunk(b"IHDR", header)
        + _png_chunk(b"IDAT", zlib.compress(bytes(raw), level=9))
        + _png_chunk(b"IEND", b"")
    )


def _set_pixel(
    pixels: bytearray,
    width: int,
    height: int,
    x: int,
    y: int,
    color: tuple[int, int, int],
) -> None:
    if x < 0 or y < 0 or x >= width or y >= height:
        return
    offset = (y * width + x) * 3
    pixels[offset : offset + 3] = bytes(color)


def _line(
    pixels: bytearray,
    width: int,
    height: int,
    start: tuple[int, int],
    end: tuple[int, int],
    color: tuple[int, int, int],
) -> None:
    x0, y0 = start
    x1, y1 = end
    dx = abs(x1 - x0)
    sx = 1 if x0 < x1 else -1
    dy = -abs(y1 - y0)
    sy = 1 if y0 < y1 else -1
    err = dx + dy
    while True:
        _set_pixel(pixels, width, height, x0, y0, color)
        _set_pixel(pixels, width, height, x0, y0 + 1, color)
        if x0 == x1 and y0 == y1:
            break
        e2 = 2 * err
        if e2 >= dy:
            err += dy
            x0 += sx
        if e2 <= dx:
            err += dx
            y0 += sy


def _equity_png(equity_curve: pd.Series, width: int = 900, height: int = 320) -> bytes:
    values = equity_curve.dropna().astype(float).tolist()
    if not values:
        values = [1.0, 1.0]
    if len(values) == 1:
        values = [values[0], values[0]]

    low = min(values)
    high = max(values)
    if math.isclose(low, high):
        low -= 1.0
        high += 1.0

    pixels = bytearray([255, 255, 255] * width * height)
    margin = 40
    chart_w = width - margin * 2
    chart_h = height - margin * 2
    axis = (208, 213, 221)
    grid = (235, 238, 242)
    line = (24, 111, 175)

    for i in range(5):
        y = margin + round(chart_h * i / 4)
        _line(pixels, width, height, (margin, y), (width - margin, y), grid)
    _line(pixels, width, height, (margin, margin), (margin, height - margin), axis)
    _line(
        pixels,
        width,
        height,
        (margin, height - margin),
        (width - margin, height - margin),
        axis,
    )

    points: list[tuple[int, int]] = []
    for i, value in enumerate(values):
        x = margin + round(chart_w * i / max(1, len(values) - 1))
        normalized = (value - low) / (high - low)
        y = height - margin - round(chart_h * normalized)
        points.append((x, y))
    for start, end in zip(points, points[1:], strict=False):
        _line(pixels, width, height, start, end, line)
    return _encode_png(width, height, pixels)


def _fmt_pct(value: float) -> str:
    return f"{value:.2%}"


def _fmt_num(value: float) -> str:
    if math.isinf(value):
        return "inf"
    return f"{value:.2f}"


def _metric_table(result: BacktestResult, metrics: Metrics) -> str:
    rows = [
        ("Total return", _fmt_pct(result.total_return)),
        ("Buy and hold", _fmt_pct(result.buy_hold)),
        ("Sharpe", _fmt_num(metrics.sharpe)),
        ("CAGR", _fmt_pct(metrics.cagr)),
        ("Max drawdown", _fmt_pct(metrics.max_drawdown)),
        ("Profit factor", _fmt_num(metrics.profit_factor)),
        ("Win rate", _fmt_pct(metrics.win_rate)),
        ("Trades", str(metrics.n_trades)),
    ]
    body = "\n".join(
        f"<tr><th>{html.escape(name)}</th><td>{html.escape(value)}</td></tr>"
        for name, value in rows
    )
    return f'<table class="metrics"><tbody>{body}</tbody></table>'


def _default_fold(symbol: str, result: BacktestResult, metrics: Metrics) -> FoldReportRow:
    start = str(result.equity_curve.index.min()) if not result.equity_curve.empty else ""
    end = str(result.equity_curve.index.max()) if not result.equity_curve.empty else ""
    return FoldReportRow(
        name=symbol,
        start=start,
        end=end,
        total_return=result.total_return,
        sharpe=metrics.sharpe,
        max_drawdown=metrics.max_drawdown,
        n_trades=metrics.n_trades,
    )


def _fold_table(rows: Sequence[FoldReportRow]) -> str:
    body = "\n".join(
        "<tr>"
        f"<td>{html.escape(row.name)}</td>"
        f"<td>{html.escape(row.start)}</td>"
        f"<td>{html.escape(row.end)}</td>"
        f"<td>{_fmt_pct(row.total_return)}</td>"
        f"<td>{_fmt_num(row.sharpe)}</td>"
        f"<td>{_fmt_pct(row.max_drawdown)}</td>"
        f"<td>{row.n_trades}</td>"
        "</tr>"
        for row in rows
    )
    return (
        '<table class="folds">'
        "<thead><tr><th>Fold</th><th>Start</th><th>End</th><th>Return</th>"
        "<th>Sharpe</th><th>Max DD</th><th>Trades</th></tr></thead>"
        f"<tbody>{body}</tbody></table>"
    )


def _regime_table(rows: Sequence[RegimeReportRow]) -> str:
    body = "\n".join(
        "<tr>"
        f"<td>{html.escape(row.regime)}</td>"
        f"<td>{row.n_periods}</td>"
        f"<td>{_fmt_pct(row.share)}</td>"
        f"<td>{_fmt_num(row.sharpe)}</td>"
        f"<td>{_fmt_pct(row.cagr)}</td>"
        f"<td>{_fmt_pct(row.max_drawdown)}</td>"
        f"<td>{_fmt_pct(row.win_rate)}</td>"
        "</tr>"
        for row in rows
    )
    return (
        '<table class="regimes">'
        "<thead><tr><th>Regime</th><th>Bars</th><th>Share</th><th>Sharpe</th>"
        "<th>CAGR</th><th>Max DD</th><th>Win rate</th></tr></thead>"
        f"<tbody>{body}</tbody></table>"
    )


def _monte_carlo_table(result: MonteCarloResult) -> str:
    confidence = f"{result.confidence:.0%}"
    body = "\n".join(
        "<tr>"
        f"<td>{html.escape(row.name)}</td>"
        f"<td>{_fmt_pct(row.final_return_low)}</td>"
        f"<td>{_fmt_pct(row.final_return_median)}</td>"
        f"<td>{_fmt_pct(row.final_return_high)}</td>"
        f"<td>{_fmt_pct(row.max_drawdown_low)}</td>"
        f"<td>{_fmt_pct(row.max_drawdown_median)}</td>"
        f"<td>{_fmt_pct(row.max_drawdown_high)}</td>"
        "</tr>"
        for row in result.methods
    )
    seed = "none" if result.seed is None else str(result.seed)
    return (
        f'<p class="note">{result.simulations} simulations, seed={html.escape(seed)}, '
        f"{html.escape(confidence)} confidence band.</p>"
        '<table class="montecarlo">'
        "<thead><tr><th>Method</th><th>Return low</th><th>Return median</th>"
        "<th>Return high</th><th>Max DD low</th><th>Max DD median</th>"
        "<th>Max DD high</th></tr></thead>"
        f"<tbody>{body}</tbody></table>"
    )


def _section_html(section: BacktestReportSection) -> str:
    png = base64.b64encode(_equity_png(section.result.equity_curve)).decode("ascii")
    folds = section.folds or (_default_fold(section.symbol, section.result, section.metrics),)
    regime_block = (
        f"""
  <h3>By regime</h3>
  {_regime_table(section.regimes)}"""
        if section.regimes
        else ""
    )
    monte_carlo_block = (
        f"""
  <h3>Monte Carlo robustness</h3>
  {_monte_carlo_table(section.monte_carlo)}"""
        if section.monte_carlo
        else ""
    )
    return f"""
<section>
  <h2>{html.escape(section.symbol)}</h2>
  <img class="equity" alt="{html.escape(section.symbol)} equity curve" src="data:image/png;base64,{png}">
  <div class="tables">
    {_metric_table(section.result, section.metrics)}
    {_fold_table(folds)}
  </div>{regime_block}{monte_carlo_block}
</section>
""".strip()


def render_html_report(
    result: BacktestResult,
    *,
    symbol: str = "Backtest",
    metrics: Metrics | None = None,
    folds: Sequence[FoldReportRow] | None = None,
    title: str = "confscan backtest report",
) -> str:
    section = BacktestReportSection(
        symbol=symbol,
        result=result,
        metrics=metrics or Metrics.from_result(result),
        folds=tuple(folds or ()),
        monte_carlo=None,
    )
    return render_html_document([section], title=title)


def render_html_document(
    sections: Sequence[BacktestReportSection],
    *,
    title: str = "confscan backtest report",
) -> str:
    rendered_sections = "\n".join(_section_html(section) for section in sections)
    escaped_title = html.escape(title)
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{escaped_title}</title>
  <style>
    body {{ font-family: system-ui, -apple-system, Segoe UI, sans-serif; margin: 32px; color: #17202a; }}
    h1 {{ font-size: 28px; margin: 0 0 24px; }}
    h2 {{ font-size: 20px; margin: 28px 0 12px; }}
    h3 {{ font-size: 16px; margin: 20px 0 8px; color: #45526a; }}
    .note {{ color: #596579; font-size: 13px; margin: 0 0 8px; }}
    .equity {{ width: 100%; max-width: 900px; height: auto; border: 1px solid #d7dde5; }}
    .tables {{ display: grid; grid-template-columns: minmax(220px, 320px) minmax(360px, 1fr); gap: 24px; margin-top: 16px; }}
    table {{ border-collapse: collapse; width: 100%; font-size: 14px; }}
    th, td {{ border: 1px solid #d7dde5; padding: 8px 10px; text-align: right; }}
    th:first-child, td:first-child, .metrics th {{ text-align: left; }}
    thead th {{ background: #f4f6f8; }}
    @media (max-width: 760px) {{ body {{ margin: 18px; }} .tables {{ grid-template-columns: 1fr; }} }}
  </style>
</head>
<body>
  <h1>{escaped_title}</h1>
  {rendered_sections}
</body>
</html>
"""


def write_html_report(
    path: str | Path,
    sections: Sequence[BacktestReportSection],
    *,
    title: str = "confscan backtest report",
) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(render_html_document(sections, title=title), encoding="utf-8")
    return target
