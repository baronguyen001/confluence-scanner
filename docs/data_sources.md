# Data Sources

The default adapters are free-first:

- Binance spot klines and futures public endpoints.
- Bybit public funding history (a second funding-rate source; select with `data.funding_source`).
- CoinGecko market-cap universe data.
- GeckoTerminal pool search.
- DefiLlama protocol TVL.

Optional paid or key-gated sources are off by default. The public package does not ship browser scraping adapters. Configure keys only through environment variables and never commit `.env`.
