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

- Pure-pandas TA: EMA, RSI, MACD, Bollinger Bands, ATR. No TA-Lib and no pandas-ta.
- Adaptive confluence scoring across TA, fundamentals, CEX flow, and on-chain layers.
- Walk-forward splitting with a no-leakage assertion and robust/overfit labels.
- Signal-driven long-only backtest engine with fees and optional stops supplied by the caller.
- Public data adapters for Binance, CoinGecko, GeckoTerminal, and DefiLlama.
- Telegram alerts with chunking and retry handling.
- Optional Gemini commentary that is neutral, generic, and never trading advice.
- Scheduler emitters for cron, launchd, and Windows Task Scheduler.

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

PyPI publishing is pending for v0.1. Until then, install from source.

## Trawlkit Case Study

`confluence-scanner` is one application of the same loop Trawlkit packages for automation work:

```text
scrape -> score -> AI -> alert -> schedule
```

See [Trawlkit](https://github.com/barobaonguyen/trawlkit) for the reusable kit, and [ai-automation-skills](https://github.com/barobaonguyen/ai-automation-skills) for free companion material.

MIT licensed.
