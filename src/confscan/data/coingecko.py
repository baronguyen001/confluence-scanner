"""CoinGecko public market data."""

from __future__ import annotations

from confscan.data.http import get_json

COINGECKO_BASE = "https://api.coingecko.com/api/v3"


def top_coins(n: int = 25) -> list[dict]:
    out: list[dict] = []
    per_page = 250
    pages = max(1, (n + per_page - 1) // per_page)
    for page in range(1, pages + 1):
        data = get_json(
            f"{COINGECKO_BASE}/coins/markets",
            params={
                "vs_currency": "usd",
                "order": "market_cap_desc",
                "per_page": per_page,
                "page": page,
                "sparkline": "false",
                "price_change_percentage": "24h,7d,30d",
            },
        )
        out.extend(data)
        if len(out) >= n:
            break
    return out[:n]
