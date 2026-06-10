# confluence-scanner

Walk-forward-first crypto signal framework. Stop deploying overfit strategies.

[![CI](https://github.com/barobaonguyen/confluence-scanner/actions/workflows/ci.yml/badge.svg)](https://github.com/barobaonguyen/confluence-scanner/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB.svg)](pyproject.toml)

![Equity curve demo](screenshots/hero_equity_curve.png)

Most crypto signal repos show a backtest and stop there. `confluence-scanner` starts with walk-forward validation: tune on one window, validate on the next, repeat, and label ideas as robust or overfit before they reach alerts.

This is a framework, bring your own thresholds. The example config uses placeholder weights and textbook indicator settings. The production edge is intentionally not included.

## 30-second example

```bash
pip install -e .
confscan scan --config examples/btc_eth_solana/config.yaml
confscan backtest --config examples/btc_eth_solana/config.yaml --html reports/backtest.html
confscan walkforward --config examples/btc_eth_solana/config.yaml
```

```python
from confscan import ConfluenceScorer, ema, detect_cross, klines, run_backtest

df = klines("BTCUSDT", interval="4h", lookback="180d")
fast = ema(df["close"], 12)
slow = ema(df["close"], 26)
cross = detect_cross(fast, slow)

result = run_backtest(df, cross == 1, cross == -1, fee_bps=10)
score = ConfluenceScorer().score(
    "BTCUSDT",
    {"ta": 65, "fa": 50, "cex": 55, "onchain": 0},
    present={"ta": True, "fa": True, "cex": True, "onchain": False},
)
print(result.metrics)
print(score.to_dict())
```

## What's In The Box

- Pure-pandas TA: EMA, RSI, MACD, Bollinger Bands, ATR, and ADX. No TA-Lib and no pandas-ta.
- Adaptive confluence scoring across TA, fundamentals, CEX flow, and on-chain layers.
- Optional ADX/ATR confluence inputs with zero default weight, so shipped scoring behavior stays unchanged until you opt in.
- Two independent funding-rate sources (Binance and Bybit) selectable via config, so a single venue outage does not blank the CEX layer.
- Walk-forward splitting with a no-leakage assertion and robust/overfit labels.
- Signal-driven long-only backtest engine with fees and optional stops supplied by the caller.
- Per-regime backtest metrics (bull/bear/chop) in the table and HTML report via `--by-regime`.
- HTML backtest reports with an embedded equity curve PNG, metrics, and per-fold tables.
- A single static HTML dashboard aggregating the latest scan and recent backtest reports.
- Public data adapters for Binance, Bybit, CoinGecko, GeckoTerminal, and DefiLlama.
- Telegram and Discord webhook alerts with chunking and retry handling.
- Optional Gemini commentary that is neutral, generic, and never trading advice.
- Scheduler emitters for cron, launchd, and Windows Task Scheduler.

## Alerts

Choose an alert route in config:

```yaml
alert:
  channel: both  # telegram, discord, or both
```

Secrets stay in environment variables:

```text
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id
DISCORD_WEBHOOK_URL=your_discord_webhook_url
```

## HTML Reports

```bash
confscan backtest --config examples/btc_eth_solana/config.yaml --html reports/backtest.html
```

The report embeds a generated PNG equity curve and includes metrics plus a compact fold table for each configured symbol.

## Funding Source

The CEX funding sub-score can read from Binance, Bybit, or an average of both. The default is `binance`, so shipped behavior is unchanged. Both sources normalize to the same `['fundingRate']` frame, so picking a source is a one-line config change:

```yaml
data:
  funding_source: both  # binance (default), bybit, or both
```

`both` averages overlapping timestamps and falls back to whichever venue returned data, which smooths over a single exchange's outage. You can also set `CONFSCAN_FUNDING_SOURCE` in the environment.

## Regime Split

Slice backtest metrics by market regime to see where an idea actually works instead of trusting one blended number:

```bash
confscan backtest --config examples/btc_eth_solana/config.yaml --by-regime --html reports/backtest.html
```

Each bar is labelled `bull`, `bear`, or `chop` from a simple, generic trend/volatility rule (a trend-EMA slope compared against a volatility band). The console table and the HTML report then show Sharpe, CAGR, max drawdown, and win rate per regime. The rule is intentionally generic, not a tuned production filter.

## Dashboard

Render a single self-contained HTML page (no JavaScript) that aggregates the latest scan output and links to the most recent backtest reports:

```bash
confscan dashboard --config examples/btc_eth_solana/config.yaml --out dashboard.html --reports-dir reports
```

The dashboard is a static file you can open directly or host anywhere. It discovers recent `*.html` reports in `--reports-dir` and links to them relative to the dashboard's own location.

## Walk-Forward Demo

The differentiator is in [`examples/walk_forward_demo`](examples/walk_forward_demo/). It uses an offline OHLCV fixture, splits rolling train/validation windows, and plots in-sample versus out-of-sample Sharpe divergence.

![Walk-forward split](screenshots/walk_forward_split_viz.png)

## Honest Rejections

[`examples/rejected_experiments`](examples/rejected_experiments/) shows a generic filter idea that looks plausible and then fails to improve validation performance. This is how you reject ideas. A framework that cannot kill its darlings is overfitting.

## Bring Your Own Thresholds

This is a framework, bring your own thresholds. The public defaults are round placeholders for examples and tests. Tune your own weights, filters, stops, and universe choices on your own walk-forward process.

## Comparison

| Tool | Best for | Where this repo differs |
| --- | --- | --- |
| Freqtrade | Full trading bots | `confscan` is research/alerts first, not order routing. |
| Backtrader | General backtesting | `confscan` ships crypto data adapters and walk-forward helpers. |
| vectorbt | Fast vectorized research | `confscan` is simpler, CLI-first, and batteries-included for alerts. |

## Quickstart

```bash
python -m venv .venv
.venv\Scripts\activate  # Windows
pip install -e ".[dev,viz]"
confscan doctor
confscan scan --config examples/btc_eth_solana/config.yaml
pytest --cov=confscan --cov-fail-under=75
```

PyPI publishing is pending for v0.2. Until then, install from source.

## → Trawlkit

`confluence-scanner` is one application of the same loop Trawlkit packages for automation work:

```text
scrape -> score -> AI -> alert -> schedule
```

See [Trawlkit](https://github.com/barobaonguyen/trawlkit) for the reusable kit, and [ai-automation-skills](https://github.com/barobaonguyen/ai-automation-skills) for free companion material.

MIT licensed.
