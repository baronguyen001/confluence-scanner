"""Free-first on-chain data adapters."""

from __future__ import annotations

import pandas as pd

from confscan.data.http import get_json

GECKOTERMINAL_BASE = "https://api.geckoterminal.com/api/v2"
DEFILLAMA_BASE = "https://api.llama.fi"


def _token_lookup(included: list[dict]) -> dict[str, str]:
    out: dict[str, str] = {}
    for item in included or []:
        typ = item.get("type")
        item_id = item.get("id")
        symbol = ((item.get("attributes") or {}).get("symbol") or "").upper()
        if typ and item_id and symbol:
            out[f"{typ}/{item_id}"] = symbol
    return out


def gt_search_pools(symbol: str) -> list[dict]:
    """Search GeckoTerminal pools and aggregate buy/sell tx counts plus volume."""

    if not symbol:
        return []
    query = symbol.upper()
    try:
        data = get_json(
            f"{GECKOTERMINAL_BASE}/search/pools",
            params={"query": symbol, "include": "base_token,quote_token"},
        )
    except Exception:
        return []
    pools = data.get("data") or []
    lookup = _token_lookup(data.get("included") or [])
    out: list[dict] = []
    for pool in pools:
        attrs = pool.get("attributes") or {}
        relationships = pool.get("relationships") or {}
        base_ref = (relationships.get("base_token") or {}).get("data") or {}
        base_key = f"{base_ref.get('type')}/{base_ref.get('id')}"
        base_symbol = lookup.get(base_key, "")
        if base_symbol and base_symbol != query:
            continue
        tx24 = (attrs.get("transactions") or {}).get("h24") or {}
        volume = float((attrs.get("volume_usd") or {}).get("h24") or 0.0)
        liquidity = float(attrs.get("reserve_in_usd") or 0.0)
        out.append(
            {
                "pool_id": pool.get("id"),
                "symbol": query,
                "volume_24h_usd": volume,
                "liquidity_usd": liquidity,
                "buy_count_24h": int(tx24.get("buys") or 0),
                "sell_count_24h": int(tx24.get("sells") or 0),
            }
        )
    return out


def defillama_tvl(protocol_slug: str) -> pd.DataFrame:
    """Return protocol TVL history from DefiLlama."""

    if not protocol_slug:
        return pd.DataFrame(columns=["date", "tvl"])
    try:
        data = get_json(f"{DEFILLAMA_BASE}/protocol/{protocol_slug}")
    except Exception:
        return pd.DataFrame(columns=["date", "tvl"])
    tvl = data.get("tvl") or []
    if not tvl:
        return pd.DataFrame(columns=["date", "tvl"])
    df = pd.DataFrame(tvl)
    if "date" in df:
        df["date"] = pd.to_datetime(df["date"], unit="s", utc=True)
        df = df.set_index("date")
    if "totalLiquidityUSD" in df and "tvl" not in df:
        df = df.rename(columns={"totalLiquidityUSD": "tvl"})
    return df


def require_optional_key(name: str, value: str | None) -> str:
    if not value:
        raise RuntimeError(f"Set {name} to enable this optional paid data source.")
    return value
