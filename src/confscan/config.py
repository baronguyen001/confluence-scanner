"""Configuration loading and non-secret diagnostics."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv


@dataclass
class Config:
    symbols: list[str] = field(default_factory=list)
    timeframe: str = "4h"
    weights: dict[str, float] | None = None
    alert_channel: str = "telegram"
    telegram_bot_token: str | None = None
    telegram_chat_id: str | None = None
    discord_webhook_url: str | None = None
    gemini_api_key: str | None = None
    coinglass_api_key: str | None = None
    nansen_api_key: str | None = None
    bitquery_api_key: str | None = None


def _as_float_weights(raw: Any) -> dict[str, float] | None:
    if not isinstance(raw, dict):
        return None
    out: dict[str, float] = {}
    for key, value in raw.items():
        try:
            out[str(key)] = float(value)
        except (TypeError, ValueError):
            continue
    return out or None


def _alert_channel(raw: dict[str, Any]) -> str:
    alert = raw.get("alert", {})
    channel = None
    if isinstance(alert, dict):
        channel = alert.get("channel")
    channel = os.getenv("CONFSCAN_ALERT_CHANNEL") or channel or raw.get("alert_channel")
    return str(channel or "telegram").strip().lower()


def load_config(path: str = "config.yaml", env_path: str = ".env") -> Config:
    """Load YAML plus optional environment overrides.

    Missing files are allowed so `confscan doctor` can run in a fresh checkout.
    Secret values are read from environment variables, but never printed by this module.
    """

    env_file = Path(env_path)
    if env_file.exists():
        load_dotenv(env_file)

    raw: dict[str, Any] = {}
    cfg_file = Path(path)
    if cfg_file.exists():
        loaded = yaml.safe_load(cfg_file.read_text(encoding="utf-8")) or {}
        if isinstance(loaded, dict):
            raw = loaded

    symbols_raw = raw.get("symbols", [])
    symbols = [str(s).upper() for s in symbols_raw] if isinstance(symbols_raw, list) else []

    return Config(
        symbols=symbols,
        timeframe=str(raw.get("timeframe", "4h")),
        weights=_as_float_weights(raw.get("weights")),
        alert_channel=_alert_channel(raw),
        telegram_bot_token=os.getenv("TELEGRAM_BOT_TOKEN") or raw.get("telegram_bot_token"),
        telegram_chat_id=os.getenv("TELEGRAM_CHAT_ID") or raw.get("telegram_chat_id"),
        discord_webhook_url=os.getenv("DISCORD_WEBHOOK_URL"),
        gemini_api_key=os.getenv("GEMINI_API_KEY") or raw.get("gemini_api_key"),
        coinglass_api_key=os.getenv("COINGLASS_API_KEY") or raw.get("coinglass_api_key"),
        nansen_api_key=os.getenv("NANSEN_API_KEY") or raw.get("nansen_api_key"),
        bitquery_api_key=os.getenv("BITQUERY_API_KEY") or raw.get("bitquery_api_key"),
    )


def audit_config(cfg: Config) -> list[str]:
    """Return human-readable config warnings without exposing secret values."""

    warnings: list[str] = []
    if not cfg.symbols:
        warnings.append("No symbols configured; scan commands need at least one symbol.")
    if cfg.timeframe not in {"1m", "5m", "15m", "1h", "2h", "4h", "1d"}:
        warnings.append(f"Unsupported-looking timeframe: {cfg.timeframe}")
    if cfg.weights:
        total = sum(cfg.weights.values())
        if abs(total - 1.0) > 0.01:
            warnings.append(f"Weights sum to {total:.3f}; they should be close to 1.0.")
    if cfg.alert_channel not in {"telegram", "discord", "both"}:
        warnings.append(f"Unsupported alert channel: {cfg.alert_channel}")
    if bool(cfg.telegram_bot_token) ^ bool(cfg.telegram_chat_id):
        warnings.append("Telegram is partially configured; set both token and chat id.")
    if cfg.alert_channel in {"discord", "both"} and not cfg.discord_webhook_url:
        warnings.append("Discord is selected; set DISCORD_WEBHOOK_URL in the environment.")
    if cfg.coinglass_api_key:
        warnings.append("Coinglass key detected, but confscan does not use Coinglass by default.")
    return warnings
