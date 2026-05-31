"""Adaptive layer scoring for signal confluence."""

from __future__ import annotations

import warnings
from dataclasses import asdict, dataclass

DEFAULT_WEIGHTS = {"ta": 0.40, "fa": 0.20, "cex": 0.20, "onchain": 0.20}
FALLBACK_WEIGHTS = {"ta": 0.55, "fa": 0.25, "cex": 0.20, "onchain": 0.0}


@dataclass
class LayerScore:
    name: str
    raw: float
    weight: float
    contribution: float
    reasons: list[str]


@dataclass
class ConfluenceResult:
    symbol: str
    total: float
    layers: list[LayerScore]
    weight_mode: str
    label: str

    def to_dict(self) -> dict:
        return {
            "symbol": self.symbol,
            "total": self.total,
            "weight_mode": self.weight_mode,
            "label": self.label,
            "layers": [asdict(layer) for layer in self.layers],
        }


def _label(total: float) -> str:
    if total >= 70:
        return "STRONG"
    if total >= 55:
        return "MODERATE"
    if total >= 40:
        return "WEAK"
    return "NEUTRAL"


def _normalize_weights(weights: dict[str, float]) -> dict[str, float]:
    total = sum(v for v in weights.values() if v > 0)
    if total <= 0:
        return dict(DEFAULT_WEIGHTS)
    return {k: (v / total if v > 0 else 0.0) for k, v in weights.items()}


class ConfluenceScorer:
    def __init__(
        self,
        weights: dict[str, float] | None = None,
        fallback_weights: dict[str, float] | None = None,
    ):
        self.weights = dict(weights or DEFAULT_WEIGHTS)
        self.fallback_weights = dict(fallback_weights or FALLBACK_WEIGHTS)
        for name, candidate in {
            "weights": self.weights,
            "fallback_weights": self.fallback_weights,
        }.items():
            total = sum(candidate.values())
            if abs(total - 1.0) > 0.01:
                warnings.warn(
                    f"{name} sum to {total:.3f}; normalizing at score time.", stacklevel=2
                )

    def score(
        self,
        symbol: str,
        layer_scores: dict[str, float],
        present: dict[str, bool] | None = None,
    ) -> ConfluenceResult:
        """Weighted 0..100 score with adaptive redistribution for absent layers."""

        present = present or {name: True for name in layer_scores}
        absent = {name for name, is_present in present.items() if not is_present}
        base_weights = self.fallback_weights if absent else self.weights
        active_weights = {
            name: weight
            for name, weight in base_weights.items()
            if present.get(name, True) or weight > 0
        }
        for name in absent:
            if name in active_weights and self.fallback_weights.get(name, 0.0) <= 0:
                active_weights[name] = 0.0
        active_weights = _normalize_weights(active_weights)

        layers: list[LayerScore] = []
        total = 0.0
        for name, weight in active_weights.items():
            raw = float(layer_scores.get(name, 0.0))
            raw = max(0.0, min(100.0, raw))
            contribution = raw * weight
            total += contribution
            reasons = ["present"] if present.get(name, True) else ["absent; redistributed"]
            layers.append(
                LayerScore(
                    name=name,
                    raw=round(raw, 3),
                    weight=round(weight, 6),
                    contribution=round(contribution, 3),
                    reasons=reasons,
                )
            )

        total = round(total, 3)
        return ConfluenceResult(
            symbol=symbol,
            total=total,
            layers=layers,
            weight_mode="fallback" if absent else "full",
            label=_label(total),
        )

    def explain(self, result: ConfluenceResult) -> dict:
        return {
            "symbol": result.symbol,
            "total": result.total,
            "label": result.label,
            "weight_mode": result.weight_mode,
            "layers": [
                {
                    "name": layer.name,
                    "raw": layer.raw,
                    "weight": layer.weight,
                    "contribution": layer.contribution,
                    "reasons": layer.reasons,
                }
                for layer in result.layers
            ],
        }


def example_ta_score(features: dict) -> tuple[float, list[str]]:
    """Generic example sub-scorer, intentionally not a tuned strategy rubric."""

    if not features.get("valid"):
        return 0.0, [str(features.get("reason", "invalid"))]
    if not features.get("cross_up"):
        return 0.0, ["no_bullish_cross"]
    score = 40.0
    reasons = ["bullish_cross"]
    if features.get("above_trend"):
        score += 20.0
        reasons.append("above_trend")
    if features.get("trend_slope_pos"):
        score += 20.0
        reasons.append("trend_slope_positive")
    if features.get("vol_confirm"):
        score += 10.0
        reasons.append("volume_confirmed")
    if features.get("stretch_ok"):
        score += 10.0
        reasons.append("not_extended")
    return min(100.0, score), reasons


def example_momentum_score(change_short: float | None, change_medium: float | None) -> float:
    """Map generic short/medium momentum inputs to 0..100."""

    short = 0.0 if change_short is None else float(change_short)
    medium = 0.0 if change_medium is None else float(change_medium)
    score = 50.0 + max(-20.0, min(20.0, short)) + max(-30.0, min(30.0, medium)) / 2
    return max(0.0, min(100.0, score))
