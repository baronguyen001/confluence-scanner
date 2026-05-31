from __future__ import annotations

from confscan.cli import main

if __name__ == "__main__":
    raise SystemExit(main(["scan", "--config", "examples/btc_eth_solana/config.yaml"]))
