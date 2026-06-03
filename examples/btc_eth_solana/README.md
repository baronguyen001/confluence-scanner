# BTC / ETH / SOL Example

This example scans three liquid symbols with public Binance data and placeholder layer weights.

```bash
confscan scan --config examples/btc_eth_solana/config.yaml
confscan backtest --config examples/btc_eth_solana/config.yaml --html reports/backtest.html
```

Alerts are optional. Set `TELEGRAM_BOT_TOKEN` plus `TELEGRAM_CHAT_ID`, `DISCORD_WEBHOOK_URL`, or both in `.env`, then choose `alert.channel` in config.

The weights are not tuned values. Treat the file as a starting point for your own walk-forward process.
