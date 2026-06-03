from __future__ import annotations

import pandas as pd

from confscan import cli


def test_cli_scan_prints_table(monkeypatch, tmp_path, capsys) -> None:
    cfg = tmp_path / "config.yaml"
    cfg.write_text("symbols: [BTCUSDT]\ntimeframe: 4h\n", encoding="utf-8")
    idx = pd.date_range("2024-01-01", periods=140, freq="4h", tz="UTC")
    df = pd.DataFrame(
        {
            "open": range(140),
            "high": [v + 2 for v in range(140)],
            "low": [v - 1 for v in range(140)],
            "close": range(140),
            "volume": [100] * 140,
        },
        index=idx,
        dtype=float,
    )
    monkeypatch.setattr(cli.binance, "klines", lambda *a, **k: df)
    monkeypatch.setattr("confscan.cli.funding_score", lambda symbol: 0.5)
    assert cli.main(["scan", "--config", str(cfg)]) == 0
    out = capsys.readouterr().out
    assert "BTCUSDT" in out
    assert "TOTAL" in out


def test_cli_doctor_masks_keys(monkeypatch, tmp_path, capsys) -> None:
    cfg = tmp_path / "config.yaml"
    cfg.write_text("symbols: [BTCUSDT]\n", encoding="utf-8")
    monkeypatch.setenv("GEMINI_API_KEY", "not_printed")
    monkeypatch.setattr("confscan.cli.get_json", lambda *a, **k: {"ok": True})
    assert cli.main(["doctor", "--config", str(cfg)]) == 0
    out = capsys.readouterr().out
    assert "not_printed" not in out
    assert "Gemini: present" in out


def test_cli_schedule(capsys) -> None:
    assert cli.main(["schedule", "--config", "x.yaml", "--os", "linux", "--at", "08:30"]) == 0
    assert "confscan scan --config x.yaml" in capsys.readouterr().out


def test_cli_backtest(monkeypatch, tmp_path, tiny_ohlcv, capsys) -> None:
    cfg = tmp_path / "config.yaml"
    cfg.write_text("symbols: [BTCUSDT]\ntimeframe: 4h\n", encoding="utf-8")
    html = tmp_path / "report.html"
    monkeypatch.setattr(cli.binance, "klines", lambda *a, **k: tiny_ohlcv)
    assert cli.main(["backtest", "--config", str(cfg), "--fee-bps", "0", "--html", str(html)]) == 0
    out = capsys.readouterr().out
    assert "BTCUSDT" in out
    assert "HTML report" in out
    assert "data:image/png;base64" in html.read_text(encoding="utf-8")


def test_cli_walkforward(monkeypatch, tmp_path, sample_ohlcv, capsys) -> None:
    cfg = tmp_path / "config.yaml"
    cfg.write_text("symbols: [BTCUSDT]\ntimeframe: 4h\n", encoding="utf-8")
    monkeypatch.setattr(cli.binance, "klines", lambda *a, **k: sample_ohlcv)
    assert (
        cli.main(
            [
                "walkforward",
                "--config",
                str(cfg),
                "--train-days",
                "20",
                "--val-days",
                "5",
                "--step-days",
                "5",
            ]
        )
        == 0
    )
    assert "verdict" in capsys.readouterr().out
