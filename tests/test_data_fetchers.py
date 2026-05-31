from __future__ import annotations

import pandas as pd

from confscan.data import binance, coingecko, onchain
from confscan.data.cache import DiskCache


def test_binance_klines_parse(monkeypatch) -> None:
    rows = [
        [1704067200000, "1", "2", "0.5", "1.5", "10", 0, "0", 0, "0", "0", "0"],
        [1704081600000, "1.5", "2.5", "1", "2", "20", 0, "0", 0, "0", "0", "0"],
    ]
    monkeypatch.setattr(binance, "get_json", lambda *a, **k: rows)
    df = binance.klines("BTCUSDT")
    assert list(df.columns) == ["open", "high", "low", "close", "volume"]
    assert df.index.tz is not None
    assert float(df["close"].iloc[-1]) == 2.0


def test_funding_and_perp_fetchers(monkeypatch) -> None:
    def fake_get_json(url, params=None, **kwargs):
        if "fundingRate" in url:
            return [{"fundingTime": 1704067200000, "fundingRate": "0.0001"}]
        if "openInterestHist" in url:
            return [{"timestamp": 1704067200000, "sumOpenInterestValue": "10"}]
        return [{"longShortRatio": "1.2"}]

    monkeypatch.setattr(binance, "get_json", fake_get_json)
    assert binance.funding_rate("BTCUSDT")["fundingRate"].iloc[0] == 0.0001
    assert isinstance(binance.open_interest("BTCUSDT"), pd.DataFrame)
    assert binance.long_short_ratio("BTCUSDT") == 1.2


def test_coingecko_top_coins(monkeypatch) -> None:
    monkeypatch.setattr(coingecko, "get_json", lambda *a, **k: [{"symbol": "btc"}])
    assert coingecko.top_coins(1)[0]["symbol"] == "btc"


def test_onchain_parse(monkeypatch) -> None:
    payload = {
        "data": [
            {
                "id": "eth_0xabc",
                "attributes": {
                    "volume_usd": {"h24": "1000"},
                    "reserve_in_usd": "5000",
                    "transactions": {"h24": {"buys": 3, "sells": 2}},
                },
                "relationships": {"base_token": {"data": {"type": "token", "id": "eth_0xabc"}}},
            }
        ],
        "included": [{"type": "token", "id": "eth_0xabc", "attributes": {"symbol": "ABC"}}],
    }
    monkeypatch.setattr(onchain, "get_json", lambda *a, **k: payload)
    pools = onchain.gt_search_pools("ABC")
    assert pools[0]["buy_count_24h"] == 3


def test_disk_cache_hard_cap(tmp_path) -> None:
    cache = DiskCache(str(tmp_path), ttl_seconds=999, max_ttl_seconds=1)
    cache.set("k", {"v": 1})
    assert cache.get("k") == {"v": 1}
