from __future__ import annotations

from confscan.config import Config, audit_config, load_config


def test_load_config_yaml_and_env(tmp_path, monkeypatch) -> None:
    cfg_path = tmp_path / "config.yaml"
    cfg_path.write_text(
        "symbols: [btc]\ntimeframe: weird\nweights:\n  ta: 0.8\n  fa: bad\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "token")
    cfg = load_config(str(cfg_path), env_path=str(tmp_path / ".env"))
    assert cfg.symbols == ["BTC"]
    assert cfg.weights == {"ta": 0.8}
    warnings = audit_config(cfg)
    assert any("timeframe" in warning for warning in warnings)
    assert any("Telegram" in warning for warning in warnings)


def test_audit_config_empty() -> None:
    warnings = audit_config(Config())
    assert any("No symbols" in warning for warning in warnings)


def test_load_config_alert_channel_and_discord_env(tmp_path, monkeypatch) -> None:
    cfg_path = tmp_path / "config.yaml"
    cfg_path.write_text(
        "symbols: [btc]\nalert:\n  channel: both\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("DISCORD_WEBHOOK_URL", "https://example.invalid/webhook")
    cfg = load_config(str(cfg_path), env_path=str(tmp_path / ".env"))
    assert cfg.alert_channel == "both"
    assert cfg.discord_webhook_url == "https://example.invalid/webhook"
    assert not any("Discord" in warning for warning in audit_config(cfg))


def test_audit_config_warns_for_selected_discord_without_webhook() -> None:
    warnings = audit_config(Config(symbols=["BTCUSDT"], alert_channel="discord"))
    assert any("Discord" in warning for warning in warnings)
