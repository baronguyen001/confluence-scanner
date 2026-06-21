# Changelog

## v0.5.0 - 2026-06-21

- Added three generic, textbook indicators to `confscan.signals.ta`: `stochastic`
  (%K/%D), `obv` (on-balance volume), and `mfi` (money flow index). Pure pandas,
  generic default periods — additional optional inputs, not a tuned edge.
- Added OKX as a third independent funding-rate source (`confscan.data.okx`),
  normalized to the same `['fundingRate']` frame as Binance/Bybit and selectable
  via `data.funding_source = okx`. Default stays `binance`, so shipped behavior is
  unchanged; fixtured tests, no live calls in CI.
- Kept scoring defaults generic; no production weights, thresholds, EMA tuning,
  or rejected-experiment figures added.

## v0.4.0 - 2026-06-11

- Added an optional public order-flow signal layer from free Binance futures endpoints for open-interest rank, long/short account ratio, and liquidation balance. The confluence layer ships with default weight `0.0`, so public scoring behavior is unchanged until a caller opts in.
- Added Monte Carlo backtest robustness diagnostics via `confscan backtest --montecarlo N`, with deterministic `--montecarlo-seed`, trade-order shuffle, bootstrap simulation, and HTML report confidence-band tables.
- Added Slack webhook alerts through `SLACK_WEBHOOK_URL`, plus `alert.channel` parsing for `telegram`, `discord`, `slack`, `all`, legacy `both`, and explicit channel combinations.
- Kept public scoring defaults generic; no production weights, EMA tuning, stop-loss settings, alert secrets, or rejected-experiment figures are included.

## v0.3.0 - 2026-06-10

- Added a second public funding-rate source (Bybit) normalized to the Binance funding-frame shape, with `data.funding_source = binance | bybit | both` selection (default `binance`, behavior unchanged) and a `both` mode that averages overlapping timestamps.
- Added generic bull/bear/chop regime classification and per-regime backtest metrics, surfaced in the console table and HTML report via `confscan backtest --by-regime`.
- Added `confscan dashboard --out dashboard.html`, a single self-contained, JavaScript-free HTML page aggregating the latest scan output and links to recent backtest reports.
- Kept public scoring defaults generic; the new regime rule and funding source add no production tuning, thresholds, or secrets.

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
