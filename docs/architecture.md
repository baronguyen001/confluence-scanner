# Architecture

`confluence-scanner` is a Trawlkit case study: the same automation loop applied to crypto signal research.

```text
scrape                         score              AI (optional)       alert            schedule (optional)
data/binance, coingecko,   ->   score/confluence -> commentary/gemini -> alert/telegram -> schedule/cron
onchain free adapters           ConfluenceScorer    neutral narration    TelegramAlerter   emit_* configs
```

The package keeps the workflow explicit:

- Data modules normalize public API responses into pandas-friendly shapes.
- Signal modules compute pure-pandas features.
- The scorer accepts caller-provided layer scores and redistributes absent layers instead of silently inflating totals.
- Backtests use caller-provided entry and exit signals.
- Walk-forward validation is the default research habit.

See [Trawlkit](https://github.com/barobaonguyen/trawlkit) for the reusable automation kit.
