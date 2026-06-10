from __future__ import annotations

import re
from pathlib import Path

from confscan.dashboard import (
    DashboardData,
    ReportLink,
    ScanRow,
    find_report_links,
    render_dashboard,
    write_dashboard,
)


def _sample_data() -> DashboardData:
    return DashboardData(
        scan_rows=[
            ScanRow(
                symbol="BTCUSDT",
                total=72.5,
                label="STRONG",
                weight_mode="full",
                layers="ta=60.0 fa=50.0 cex=55.0 onchain=0.0",
            ),
            ScanRow(
                symbol="ETHUSDT",
                total=41.0,
                label="WEAK",
                weight_mode="fallback",
                layers="ta=40.0 fa=45.0 cex=50.0",
            ),
        ],
        report_links=[ReportLink(label="backtest.html", href="reports/backtest.html")],
        generated_at="2026-06-10 00:00 UTC",
        funding_source="both",
        timeframe="4h",
    )


def test_render_dashboard_is_self_contained_html() -> None:
    html = render_dashboard(_sample_data())
    assert html.startswith("<!doctype html>")
    assert "<html" in html and "</html>" in html
    # No JavaScript dependency.
    assert "<script" not in html.lower()
    assert "BTCUSDT" in html
    assert "STRONG" in html
    assert "reports/backtest.html" in html
    assert "both" in html  # funding source surfaced
    # Roughly balanced tags as a sanity check on the static markup.
    assert html.count("<table") == html.count("</table>")


def test_render_dashboard_escapes_content() -> None:
    data = DashboardData(
        scan_rows=[
            ScanRow(
                symbol="<x>",
                total=1.0,
                label="NEUTRAL",
                weight_mode="full",
                layers="a & b",
            )
        ]
    )
    html = render_dashboard(data)
    assert "<x>" not in html
    assert "&lt;x&gt;" in html
    assert "a &amp; b" in html


def test_render_dashboard_empty_state() -> None:
    html = render_dashboard(DashboardData())
    assert "No scan results" in html
    assert "No backtest reports" in html


def test_find_report_links_orders_newest_first(tmp_path) -> None:
    reports = tmp_path / "reports"
    reports.mkdir()
    older = reports / "old.html"
    newer = reports / "new.html"
    older.write_text("old", encoding="utf-8")
    newer.write_text("new", encoding="utf-8")
    import os

    os.utime(older, (1_000_000, 1_000_000))
    os.utime(newer, (2_000_000, 2_000_000))

    links = find_report_links(reports, base=tmp_path)
    assert [link.label for link in links] == ["new.html", "old.html"]
    # Hrefs are relative to the dashboard output base.
    assert links[0].href == "reports/new.html"


def test_find_report_links_missing_dir(tmp_path) -> None:
    assert find_report_links(tmp_path / "nope") == []


def test_write_dashboard_creates_file(tmp_path) -> None:
    out = tmp_path / "out" / "dashboard.html"
    written = write_dashboard(out, _sample_data())
    assert written == out
    text = out.read_text(encoding="utf-8")
    assert "confscan dashboard" in text
    assert isinstance(written, Path)


def test_dashboard_html_has_no_external_resources() -> None:
    html = render_dashboard(_sample_data())
    # No remote stylesheets/scripts/images embedded.
    assert not re.search(r'src="https?://', html)
    assert not re.search(r'href="https?://', html)
