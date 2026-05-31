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
