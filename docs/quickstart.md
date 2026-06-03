# Quickstart

Install locally:

```bash
pip install -e ".[dev]"
confscan --help
confscan doctor
```

Run the public-data example:

```bash
confscan scan --config examples/btc_eth_solana/config.yaml
```

The output is a score table. It is not a trading recommendation. The weights in the example are placeholders for learning the workflow.

Backtest the same symbols:

```bash
confscan backtest --config examples/btc_eth_solana/config.yaml --start 2024-01-01 --end 2025-01-01
```

Add `--html reports/backtest.html` to write a self-contained report with an embedded equity curve PNG, metrics, and fold table.

Run a rolling validation pass:

```bash
confscan walkforward --config examples/btc_eth_solana/config.yaml --train-days 365 --val-days 90 --step-days 30
```
