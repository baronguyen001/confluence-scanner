from __future__ import annotations

import pandas as pd
import pytest

from confscan.backtest.walk_forward import (
    WalkForward,
    _assert_no_leakage,
    classify_robustness,
    walk_forward_split,
)


def test_walk_forward_split_no_leakage(sample_ohlcv: pd.DataFrame) -> None:
    folds = list(walk_forward_split(sample_ohlcv, train_days=20, val_days=5, step_days=5))
    assert folds
    for fold in folds:
        assert fold.train.index.max() < fold.val.index.min()


def test_walk_forward_expanding_keeps_start(sample_ohlcv: pd.DataFrame) -> None:
    folds = list(
        walk_forward_split(sample_ohlcv, train_days=20, val_days=5, step_days=5, expanding=True)
    )
    assert len(folds) >= 2
    assert folds[0].train.index.min() == folds[1].train.index.min()
    assert len(folds[1].train) > len(folds[0].train)


def test_walk_forward_class_wrapper(sample_ohlcv: pd.DataFrame) -> None:
    train, val = next(WalkForward(20, 5, 5).split(sample_ohlcv))
    assert isinstance(train, pd.DataFrame)
    assert train.index.max() < val.index.min()


def test_no_leakage_assertion_fires() -> None:
    idx = pd.date_range("2024-01-01", periods=3, freq="D", tz="UTC")
    train = pd.DataFrame({"x": [1, 2]}, index=idx[:2])
    val = pd.DataFrame({"x": [3]}, index=idx[1:2])
    with pytest.raises(AssertionError, match="leakage"):
        _assert_no_leakage(train, val)


def test_classify_robustness() -> None:
    assert classify_robustness(1, 1, 5) == "STRONG ROBUST"
    assert classify_robustness(2, 3, 5) == "robust"
    assert classify_robustness(2, 5, 5) == "OVERFIT (good train, bad val)"
    assert classify_robustness(5, 2, 5) == "underperformer"
    assert classify_robustness(4, 5, 5) == "weak both"
