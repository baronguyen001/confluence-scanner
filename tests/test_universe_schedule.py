from __future__ import annotations

from confscan.schedule.cron import emit_cron, emit_launchd, emit_windows_task
from confscan.universe import loader


def test_top_n_by_market_cap_filters_stables(monkeypatch) -> None:
    monkeypatch.setattr(
        loader,
        "top_coins",
        lambda n: [
            {"symbol": "usdc", "current_price": 1.0},
            {
                "id": "bitcoin",
                "symbol": "btc",
                "name": "Bitcoin",
                "market_cap_rank": 1,
                "market_cap": 1,
                "total_volume": 1,
            },
        ],
    )
    coins = loader.top_n_by_market_cap(1)
    assert coins[0]["symbol"] == "BTC"
    assert coins[0]["binance_spot"] == "BTCUSDT"


def test_schedule_emitters() -> None:
    assert "schtasks" in emit_windows_task("scan", "confscan scan")
    assert emit_cron("confscan scan", at="08:30").startswith("30 8")
    assert "plist" in emit_launchd("scan", "confscan scan")
