"""Command-line interface for confscan."""

from __future__ import annotations

import argparse
import os
import platform
import sys
import time
from datetime import UTC, datetime

import pandas as pd

from confscan.alert.telegram import TelegramAlerter
from confscan.backtest.engine import run_backtest
from confscan.backtest.metrics import Metrics
from confscan.backtest.walk_forward import classify_robustness, walk_forward_split
from confscan.commentary.gemini import generate_commentary
from confscan.config import Config, audit_config, load_config
from confscan.data import binance
from confscan.data.http import get_json
from confscan.schedule.cron import emit_cron, emit_launchd, emit_windows_task
from confscan.score.confluence import ConfluenceScorer, example_momentum_score, example_ta_score
from confscan.signals.funding import funding_score
from confscan.signals.ta import detect_cross, ema, ema_cross_signal


def _config_path(args: argparse.Namespace) -> str:
    return str(getattr(args, "config", "config.yaml"))


def _symbol_from_arg(symbol: str) -> str:
    symbol = symbol.upper()
    return symbol if symbol.endswith("USDT") else f"{symbol}USDT"


def _signals_for_frame(
    df: pd.DataFrame, fast: int = 12, slow: int = 26
) -> tuple[pd.Series, pd.Series]:
    crosses = detect_cross(ema(df["close"], fast), ema(df["close"], slow))
    return crosses == 1, crosses == -1


def _print_scan_row(result) -> None:
    layer_text = " ".join(f"{layer.name}={layer.raw:.1f}" for layer in result.layers)
    print(
        f"{result.symbol:<10} {result.total:>6.1f} {result.label:<9} {result.weight_mode:<8} {layer_text}"
    )


def _scan_once(cfg: Config, *, commentary: bool = False) -> int:
    if not cfg.symbols:
        print("No symbols configured.")
        return 1
    scorer = ConfluenceScorer(weights=cfg.weights)
    alerter = TelegramAlerter(cfg.telegram_bot_token or "", cfg.telegram_chat_id or "")
    print(f"{'SYMBOL':<10} {'TOTAL':>6} {'LABEL':<9} {'MODE':<8} LAYERS")
    for raw_symbol in cfg.symbols:
        symbol = _symbol_from_arg(raw_symbol)
        df = binance.klines(symbol, cfg.timeframe, limit=500)
        if df.empty:
            print(f"{symbol:<10} {'n/a':>6} {'NO_DATA':<9} {'-':<8} public kline fetch failed")
            continue
        features = ema_cross_signal(df, fast=12, slow=26, trend=100)
        ta_score, _ = example_ta_score(features)
        recent_change = (
            (df["close"].iloc[-1] / df["close"].iloc[-10] - 1.0) * 100 if len(df) >= 10 else 0.0
        )
        medium_change = (
            (df["close"].iloc[-1] / df["close"].iloc[-40] - 1.0) * 100 if len(df) >= 40 else 0.0
        )
        fa_score = example_momentum_score(float(recent_change), float(medium_change))
        cex_score = funding_score(symbol) * 100.0
        result = scorer.score(
            symbol,
            {"ta": ta_score, "fa": fa_score, "cex": cex_score, "onchain": 0.0},
            present={"ta": True, "fa": True, "cex": True, "onchain": False},
        )
        _print_scan_row(result)
        if commentary:
            text = generate_commentary(result.to_dict())
            if text:
                print(f"  commentary: {text}")
        if cfg.telegram_bot_token and cfg.telegram_chat_id:
            alerter.send_confluence(result)
    return 0


def cmd_scan(args: argparse.Namespace) -> int:
    cfg = load_config(_config_path(args))
    if not args.watch:
        return _scan_once(cfg, commentary=args.commentary)
    interval_minutes = int(os.getenv("CONFSCAN_WATCH_MINUTES", "60"))
    while True:
        rc = _scan_once(cfg, commentary=args.commentary)
        if rc:
            return rc
        time.sleep(interval_minutes * 60)


def _date_ms(value: str | None) -> int | None:
    if not value:
        return None
    dt = datetime.fromisoformat(value).replace(tzinfo=UTC)
    return int(dt.timestamp() * 1000)


def cmd_backtest(args: argparse.Namespace) -> int:
    cfg = load_config(_config_path(args))
    start_ms = _date_ms(args.start)
    end_ms = _date_ms(args.end)
    rows = []
    for raw_symbol in cfg.symbols:
        symbol = _symbol_from_arg(raw_symbol)
        df = binance.klines(symbol, cfg.timeframe, limit=3000, start_ms=start_ms, end_ms=end_ms)
        if df.empty:
            rows.append((symbol, "NO_DATA", 0.0, 0.0, 0))
            continue
        entry, exit_ = _signals_for_frame(df)
        result = run_backtest(df, entry, exit_, fee_bps=args.fee_bps)
        metrics = Metrics.from_result(result, freq=cfg.timeframe)
        rows.append(
            (
                symbol,
                f"{result.total_return:.2%}",
                metrics.sharpe,
                metrics.max_drawdown,
                metrics.n_trades,
            )
        )
    print(f"{'SYMBOL':<10} {'RETURN':>10} {'SHARPE':>8} {'MAX_DD':>9} {'TRADES':>7}")
    for symbol, ret, sharpe, max_dd, trades in rows:
        print(f"{symbol:<10} {ret:>10} {sharpe:>8.2f} {max_dd:>9.2%} {trades:>7}")
    return 0


def _rank(values: dict[str, float]) -> dict[str, int]:
    ordered = sorted(values.items(), key=lambda item: item[1], reverse=True)
    return {name: i + 1 for i, (name, _) in enumerate(ordered)}


def cmd_walkforward(args: argparse.Namespace) -> int:
    cfg = load_config(_config_path(args))
    if not cfg.symbols:
        print("No symbols configured.")
        return 1
    candidates = {"fast": (10, 24), "textbook": (12, 26), "smooth": (18, 36)}
    for raw_symbol in cfg.symbols:
        symbol = _symbol_from_arg(raw_symbol)
        df = binance.klines(symbol, cfg.timeframe, limit=5000, lookback="730d")
        if df.empty:
            print(f"{symbol}: no data")
            continue
        print(f"\n{symbol}")
        for fold_no, fold in enumerate(
            walk_forward_split(
                df,
                train_days=args.train_days,
                val_days=args.val_days,
                step_days=args.step_days,
                expanding=args.expanding,
            ),
            start=1,
        ):
            train_scores: dict[str, float] = {}
            val_scores: dict[str, float] = {}
            for name, (fast, slow) in candidates.items():
                tr_entry, tr_exit = _signals_for_frame(fold.train, fast, slow)
                va_entry, va_exit = _signals_for_frame(fold.val, fast, slow)
                train_scores[name] = Metrics.from_result(
                    run_backtest(fold.train, tr_entry, tr_exit), freq=cfg.timeframe
                ).sharpe
                val_scores[name] = Metrics.from_result(
                    run_backtest(fold.val, va_entry, va_exit), freq=cfg.timeframe
                ).sharpe
            train_rank = _rank(train_scores)
            val_rank = _rank(val_scores)
            best_train = min(train_rank, key=lambda key: train_rank[key])
            verdict = classify_robustness(
                train_rank[best_train], val_rank[best_train], len(candidates)
            )
            print(
                f"fold {fold_no}: best_train={best_train} "
                f"train_sharpe={train_scores[best_train]:.2f} "
                f"val_rank={val_rank[best_train]} verdict={verdict}"
            )
    return 0


def _ping(name: str, url: str) -> tuple[str, bool]:
    try:
        get_json(url, retries=1, timeout=8)
        return name, True
    except Exception:
        return name, False


def cmd_doctor(args: argparse.Namespace) -> int:
    cfg = load_config(_config_path(args) if getattr(args, "config", None) else "config.yaml")
    warnings = audit_config(cfg)
    print("confscan doctor")
    print("config warnings:")
    if warnings:
        for warning in warnings:
            print(f"  - {warning}")
    else:
        print("  - none")
    print("free sources:")
    for name, ok in [
        _ping("Binance", f"{binance.BINANCE_SPOT}/api/v3/time"),
        _ping("CoinGecko", "https://api.coingecko.com/api/v3/ping"),
        _ping("GeckoTerminal", "https://api.geckoterminal.com/api/v2/networks"),
    ]:
        print(f"  {'ok' if ok else 'fail'} {name}")
    print("optional keys:")
    print(f"  Gemini: {'present' if cfg.gemini_api_key else 'missing'}")
    print(f"  Nansen: {'present' if cfg.nansen_api_key else 'missing'}")
    print(f"  Bitquery: {'present' if cfg.bitquery_api_key else 'missing'}")
    return 0


def cmd_schedule(args: argparse.Namespace) -> int:
    command = f"confscan scan --config {args.config}"
    os_name = args.os or platform.system().lower()
    if os_name.startswith("win"):
        print(emit_windows_task("confscan-scan", command, at=args.at))
    elif os_name in {"mac", "darwin"}:
        print(emit_launchd("confscan.scan", command, at=args.at))
    else:
        print(emit_cron(command, at=args.at))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="confscan")
    sub = parser.add_subparsers(dest="command", required=True)

    scan = sub.add_parser("scan", help="scan symbols and print a confluence table")
    scan.add_argument("--config", default="config.yaml")
    scan.add_argument("--watch", action="store_true")
    scan.add_argument("--commentary", action="store_true")
    scan.set_defaults(func=cmd_scan)

    backtest = sub.add_parser("backtest", help="run a signal-driven backtest")
    backtest.add_argument("--config", default="config.yaml")
    backtest.add_argument("--start", default=None)
    backtest.add_argument("--end", default=None)
    backtest.add_argument("--fee-bps", type=float, default=10.0)
    backtest.set_defaults(func=cmd_backtest)

    walk = sub.add_parser("walkforward", help="run generic walk-forward validation")
    walk.add_argument("--config", default="config.yaml")
    walk.add_argument("--train-days", type=int, default=365)
    walk.add_argument("--val-days", type=int, default=90)
    walk.add_argument("--step-days", type=int, default=30)
    walk.add_argument("--expanding", action="store_true")
    walk.set_defaults(func=cmd_walkforward)

    doctor = sub.add_parser("doctor", help="check config and public data reachability")
    doctor.add_argument("--config", default=None)
    doctor.set_defaults(func=cmd_doctor)

    schedule = sub.add_parser("schedule", help="emit scheduler config")
    schedule.add_argument("--config", default="config.yaml")
    schedule.add_argument("--at", default="09:00")
    schedule.add_argument("--os", choices=["win", "linux", "mac"], default=None)
    schedule.set_defaults(func=cmd_schedule)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    sys.exit(main())
