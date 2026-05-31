"""On-chain signal facade."""

from __future__ import annotations

import warnings

from confscan.data.onchain import defillama_tvl, gt_search_pools


def onchain_score(
    symbol: str,
    *,
    network: str = "eth",
    token_address: str | None = None,
) -> float:
    """Return a generic 0..1 score from free public on-chain sources."""

    pools = gt_search_pools(token_address or symbol)
    if pools:
        buys = sum(int(p.get("buy_count_24h") or 0) for p in pools)
        sells = sum(int(p.get("sell_count_24h") or 0) for p in pools)
        volume = sum(float(p.get("volume_24h_usd") or 0.0) for p in pools)
        tx_total = buys + sells
        flow_score = buys / tx_total if tx_total else 0.5
        volume_score = min(1.0, volume / 1_000_000.0)
        return max(0.0, min(1.0, 0.7 * flow_score + 0.3 * volume_score))

    tvl = defillama_tvl(symbol.lower())
    if not tvl.empty and "tvl" in tvl:
        recent = tvl["tvl"].tail(5).astype(float)
        if len(recent) >= 2 and recent.iloc[0] > 0:
            trend = (recent.iloc[-1] - recent.iloc[0]) / recent.iloc[0]
            return max(0.0, min(1.0, 0.5 + trend))

    warnings.warn(
        f"No free on-chain data resolved for {symbol} on {network}; returning 0.0.",
        stacklevel=2,
    )
    return 0.0
