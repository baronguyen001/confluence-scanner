from __future__ import annotations

from confscan.config import Config, alert_channels, audit_config, load_config


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


def test_alert_channel_combinations_and_slack_env(tmp_path, monkeypatch) -> None:
    cfg_path = tmp_path / "config.yaml"
    cfg_path.write_text("symbols: [btc]\nalert:\n  channel: telegram+slack\n", encoding="utf-8")
    monkeypatch.setenv("SLACK_WEBHOOK_URL", "https://example.invalid/slack")

    cfg = load_config(str(cfg_path), env_path=str(tmp_path / ".env"))

    assert alert_channels(cfg.alert_channel) == {"telegram", "slack"}
    assert cfg.slack_webhook_url == "https://example.invalid/slack"
    assert not any("Slack" in warning for warning in audit_config(cfg))


def test_funding_source_default_and_selection(tmp_path, monkeypatch) -> None:
    default_cfg_path = tmp_path / "config.yaml"
    default_cfg_path.write_text("symbols: [btc]\n", encoding="utf-8")
    default_cfg = load_config(str(default_cfg_path), env_path=str(tmp_path / ".env"))
    assert default_cfg.funding_source == "binance"

    cfg_path = tmp_path / "config2.yaml"
    cfg_path.write_text("symbols: [btc]\ndata:\n  funding_source: both\n", encoding="utf-8")
    cfg = load_config(str(cfg_path), env_path=str(tmp_path / ".env"))
    assert cfg.funding_source == "both"
    assert not any("funding source" in warning for warning in audit_config(cfg))

    monkeypatch.setenv("CONFSCAN_FUNDING_SOURCE", "bybit")
    env_cfg = load_config(str(default_cfg_path), env_path=str(tmp_path / ".env"))
    assert env_cfg.funding_source == "bybit"


def test_audit_config_warns_for_bad_funding_source() -> None:
    warnings = audit_config(Config(symbols=["BTCUSDT"], funding_source="kraken"))
    assert any("funding source" in warning for warning in warnings)
