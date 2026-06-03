from __future__ import annotations

from confscan.score.confluence import ConfluenceScorer, example_ta_score


def test_confluence_full_weights() -> None:
    result = ConfluenceScorer().score(
        "BTCUSDT",
        {"ta": 80, "fa": 60, "cex": 50, "onchain": 40},
    )
    assert result.total == 62.0
    assert result.weight_mode == "full"
    assert result.label == "MODERATE"
    assert result.to_dict()["layers"][0]["name"] == "ta"
    assert [layer.name for layer in result.layers] == ["ta", "fa", "cex", "onchain"]


def test_confluence_redistributes_absent_onchain() -> None:
    result = ConfluenceScorer().score(
        "BTCUSDT",
        {"ta": 80, "fa": 60, "cex": 50, "onchain": 0},
        present={"ta": True, "fa": True, "cex": True, "onchain": False},
    )
    assert result.weight_mode == "fallback"
    assert result.total == 69.0
    assert all(layer.name != "onchain" or layer.weight == 0 for layer in result.layers)


def test_example_ta_score_is_generic() -> None:
    score, reasons = example_ta_score(
        {
            "valid": True,
            "cross_up": True,
            "above_trend": True,
            "trend_slope_pos": True,
            "vol_confirm": False,
            "stretch_ok": True,
        }
    )
    assert score == 90
    assert "bullish_cross" in reasons


def test_optional_adx_atr_layers_are_weight_configurable() -> None:
    result = ConfluenceScorer(
        weights={"ta": 0.35, "fa": 0.20, "cex": 0.20, "onchain": 0.15, "adx": 0.05, "atr": 0.05}
    ).score(
        "BTCUSDT",
        {"ta": 80, "fa": 60, "cex": 50, "onchain": 40, "adx": 30, "atr": 70},
    )
    layers = {layer.name: layer for layer in result.layers}
    assert layers["adx"].weight == 0.05
    assert layers["atr"].weight == 0.05
    assert result.total == 61.0
