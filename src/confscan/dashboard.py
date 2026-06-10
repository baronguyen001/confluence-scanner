"""Single static HTML dashboard.

Aggregates the latest confluence scan output and links to the most recent backtest
report(s) into one self-contained HTML page with no JavaScript. The render layer is
data-only so it can be unit-tested without any network access; the CLI wires a live
scan into :func:`build_dashboard`.
"""

from __future__ import annotations

import html
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path


@dataclass(frozen=True)
class ScanRow:
    symbol: str
    total: float
    label: str
    weight_mode: str
    layers: str


@dataclass(frozen=True)
class ReportLink:
    label: str
    href: str
    modified: str = ""


@dataclass
class DashboardData:
    scan_rows: list[ScanRow] = field(default_factory=list)
    report_links: list[ReportLink] = field(default_factory=list)
    generated_at: str = ""
    funding_source: str = "binance"
    timeframe: str = "4h"


def _label_class(label: str) -> str:
    return {
        "STRONG": "strong",
        "MODERATE": "moderate",
        "WEAK": "weak",
        "NEUTRAL": "neutral",
    }.get(label.upper(), "neutral")


def _scan_table(rows: Sequence[ScanRow]) -> str:
    if not rows:
        return '<p class="empty">No scan results. Run <code>confscan scan</code> first.</p>'
    body = "\n".join(
        "<tr>"
        f"<td>{html.escape(row.symbol)}</td>"
        f"<td>{row.total:.1f}</td>"
        f'<td><span class="badge {_label_class(row.label)}">{html.escape(row.label)}</span></td>'
        f"<td>{html.escape(row.weight_mode)}</td>"
        f"<td>{html.escape(row.layers)}</td>"
        "</tr>"
        for row in rows
    )
    return (
        '<table class="scan">'
        "<thead><tr><th>Symbol</th><th>Total</th><th>Label</th>"
        "<th>Mode</th><th>Layers</th></tr></thead>"
        f"<tbody>{body}</tbody></table>"
    )


def _reports_list(links: Sequence[ReportLink]) -> str:
    if not links:
        return (
            '<p class="empty">No backtest reports found. Generate one with '
            "<code>confscan backtest --html reports/backtest.html</code>.</p>"
        )
    items = "\n".join(
        "<li>"
        f'<a href="{html.escape(link.href)}">{html.escape(link.label)}</a>'
        + (f' <span class="muted">{html.escape(link.modified)}</span>' if link.modified else "")
        + "</li>"
        for link in links
    )
    return f'<ul class="reports">{items}</ul>'


def render_dashboard(data: DashboardData, *, title: str = "confscan dashboard") -> str:
    """Render a self-contained, JS-free HTML dashboard string."""

    generated = data.generated_at or datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")
    escaped_title = html.escape(title)
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{escaped_title}</title>
  <style>
    body {{ font-family: system-ui, -apple-system, Segoe UI, sans-serif; margin: 32px; color: #17202a; }}
    h1 {{ font-size: 26px; margin: 0 0 4px; }}
    .meta {{ color: #6b7888; font-size: 13px; margin: 0 0 24px; }}
    h2 {{ font-size: 18px; margin: 28px 0 10px; }}
    table {{ border-collapse: collapse; width: 100%; font-size: 14px; max-width: 900px; }}
    th, td {{ border: 1px solid #d7dde5; padding: 8px 10px; text-align: left; }}
    thead th {{ background: #f4f6f8; }}
    .badge {{ padding: 2px 8px; border-radius: 10px; font-size: 12px; font-weight: 600; }}
    .badge.strong {{ background: #d4f4dd; color: #136c34; }}
    .badge.moderate {{ background: #e6f0fb; color: #1b5fa8; }}
    .badge.weak {{ background: #fdf0d5; color: #8a5a00; }}
    .badge.neutral {{ background: #eceff3; color: #50607a; }}
    ul.reports {{ padding-left: 18px; }}
    .muted {{ color: #94a1b2; font-size: 12px; }}
    .empty {{ color: #6b7888; font-style: italic; }}
    code {{ background: #f4f6f8; padding: 1px 5px; border-radius: 4px; }}
  </style>
</head>
<body>
  <h1>{escaped_title}</h1>
  <p class="meta">Generated {html.escape(generated)} &middot; timeframe {html.escape(data.timeframe)} &middot; funding source {html.escape(data.funding_source)}</p>
  <h2>Latest scan</h2>
  {_scan_table(data.scan_rows)}
  <h2>Recent backtest reports</h2>
  {_reports_list(data.report_links)}
</body>
</html>
"""


def find_report_links(
    reports_dir: str | Path,
    *,
    base: str | Path | None = None,
    limit: int = 5,
) -> list[ReportLink]:
    """Discover recent ``*.html`` backtest reports, newest first.

    Hrefs are made relative to ``base`` (the dashboard output directory) when
    possible so the links resolve as static files next to the dashboard.
    """

    directory = Path(reports_dir)
    if not directory.exists():
        return []
    files = sorted(
        (p for p in directory.glob("*.html") if p.is_file()),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    links: list[ReportLink] = []
    base_path = Path(base) if base is not None else None
    for path in files[: max(0, limit)]:
        href = str(path)
        if base_path is not None:
            try:
                href = path.resolve().relative_to(base_path.resolve()).as_posix()
            except ValueError:
                href = path.resolve().as_posix()
        modified = datetime.fromtimestamp(path.stat().st_mtime, UTC).strftime("%Y-%m-%d %H:%M UTC")
        links.append(ReportLink(label=path.name, href=href, modified=modified))
    return links


def write_dashboard(
    path: str | Path,
    data: DashboardData,
    *,
    title: str = "confscan dashboard",
) -> Path:
    """Render the dashboard and write it to ``path``."""

    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(render_dashboard(data, title=title), encoding="utf-8")
    return target
