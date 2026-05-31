from __future__ import annotations

import pandas as pd
import pytest

from confscan.signals import funding as funding_mod
from confscan.signals import onchain as onchain_mod
from confscan.signals.sentiment import sentiment_score


def test_funding_percentile_and_score(monkeypatch) -> None:
    assert funding_mod.funding_percentile(pd.Series(dtype=float), 0.0) == 0.5
    monkeypatch.setattr(
        funding_mod,
        "funding_rate",
        lambda symbol, limit=100: pd.DataFrame({"fundingRate": [0.01, 0.02, 0.03]}),
    )
    assert funding_mod.funding_score("BTCUSDT") == 0.0


def test_onchain_score_from_pools(monkeypatch) -> None:
    monkeypatch.setattr(
        onchain_mod,
        "gt_search_pools",
        lambda symbol: [{"buy_count_24h": 7, "sell_count_24h": 3, "volume_24h_usd": 500_000}],
    )
    assert 0 < onchain_mod.onchain_score("ABC") <= 1


def test_onchain_score_from_tvl(monkeypatch) -> None:
    monkeypatch.setattr(onchain_mod, "gt_search_pools", lambda symbol: [])
    monkeypatch.setattr(
        onchain_mod,
        "defillama_tvl",
        lambda slug: pd.DataFrame({"tvl": [100.0, 110.0, 120.0]}),
    )
    assert onchain_mod.onchain_score("abc") > 0.5


def test_onchain_score_warns_without_data(monkeypatch) -> None:
    monkeypatch.setattr(onchain_mod, "gt_search_pools", lambda symbol: [])
    monkeypatch.setattr(onchain_mod, "defillama_tvl", lambda slug: pd.DataFrame())
    with pytest.warns(UserWarning):
        assert onchain_mod.onchain_score("missing") == 0.0


def test_sentiment_stub() -> None:
    assert sentiment_score("BTC") == 0.0
