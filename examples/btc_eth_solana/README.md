# BTC / ETH / SOL Example

This example scans three liquid symbols with public Binance data and placeholder layer weights.

```bash
confscan scan --config examples/btc_eth_solana/config.yaml
```

Telegram is optional. Set `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` in `.env` if you want alerts.

The weights are not tuned values. Treat the file as a starting point for your own walk-forward process.
