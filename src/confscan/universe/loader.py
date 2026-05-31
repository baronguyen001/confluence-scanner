"""CoinGecko universe selection with stable/wrapped filtering."""

from __future__ import annotations

from confscan.data.coingecko import top_coins

EXCLUDE_SYMBOLS = {
    "USDT",
    "USDC",
    "DAI",
    "BUSD",
    "FDUSD",
    "TUSD",
    "USDD",
    "USDE",
    "PYUSD",
    "FRAX",
    "USDP",
    "GUSD",
    "LUSD",
    "USTC",
    "GHO",
    "USDS",
    "USD1",
    "USDG",
    "USDY",
    "USDF",
    "USTB",
    "USDTB",
    "USYC",
    "RLUSD",
    "BFUSD",
    "U",
    "BUIDL",
    "JAAA",
    "OUSG",
    "USDM",
    "EURT",
    "EUR",
    "EURS",
    "EURC",
    "EURI",
    "WBTC",
    "WETH",
    "STETH",
    "WSTETH",
    "WEETH",
    "RETH",
    "CBETH",
    "EZETH",
    "TBTC",
    "BTCB",
    "WBETH",
    "METH",
    "WBNB",
    "WSOL",
    "WAVAX",
    "WMATIC",
    "BNSOL",
    "JITOSOL",
    "MSOL",
    "LBTC",
}


def _looks_like_stable(coin: dict) -> bool:
    price = coin.get("current_price")
    if price is None:
        return False
    try:
        current_price = float(price)
    except (TypeError, ValueError):
        return False
    if not (0.97 <= current_price <= 1.03):
        return False
    c24 = coin.get("price_change_percentage_24h_in_currency")
    c30 = coin.get("price_change_percentage_30d_in_currency")
    if c24 is not None and abs(float(c24)) > 2.0:
        return False
    return not (c30 is not None and abs(float(c30)) > 3.0)


def top_n_by_market_cap(n: int = 25) -> list[dict]:
    """Return a filtered CoinGecko market-cap universe with Binance-style symbols."""

    raw = top_coins(max(n * 2, n))
    out: list[dict] = []
    for coin in raw:
        symbol = (coin.get("symbol") or "").upper()
        if not symbol or symbol in EXCLUDE_SYMBOLS or _looks_like_stable(coin):
            continue
        out.append(
            {
                "id": coin.get("id"),
                "symbol": symbol,
                "name": coin.get("name"),
                "rank": coin.get("market_cap_rank"),
                "market_cap": coin.get("market_cap"),
                "volume_24h": coin.get("total_volume"),
                "change_24h": coin.get("price_change_percentage_24h_in_currency"),
                "change_7d": coin.get("price_change_percentage_7d_in_currency"),
                "change_30d": coin.get("price_change_percentage_30d_in_currency"),
                "binance_spot": f"{symbol}USDT",
            }
        )
        if len(out) >= n:
            break
    return out
