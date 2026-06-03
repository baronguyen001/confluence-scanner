# Changelog

## v0.2.0 - 2026-06-03

- Added Discord webhook alerts and `alert.channel` routing for Telegram, Discord, or both.
- Added HTML backtest reports with embedded equity curve PNGs, metrics, and per-fold tables via `confscan backtest --html`.
- Added pure-pandas ADX and exposed ADX/ATR as optional confluence layers with zero default weight.
- Kept public scoring defaults generic; no production tuning, thresholds, or secrets are included.

## v0.1.0 - 2026-05-31

- Initial public MIT release of `confluence-scanner`.
- Added pure-pandas TA primitives, adaptive confluence scoring, public data fetchers,
  signal-driven backtesting, walk-forward splitting, Telegram alerts, optional Gemini
  commentary, scheduler emitters, examples, docs, tests, and CI.
- Roadmap: sentiment ingestion, optional heatmap research adapter, order-routing adapters,
  regime classification, and position-sizing research modules.
