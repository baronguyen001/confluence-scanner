"""Walk-forward splitting and robustness labeling."""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass

import pandas as pd


@dataclass
class Fold:
    train_start: pd.Timestamp
    train_end: pd.Timestamp
    val_start: pd.Timestamp
    val_end: pd.Timestamp
    train: pd.DataFrame
    val: pd.DataFrame


def _validate_datetime_index(data: pd.DataFrame) -> pd.DataFrame:
    if not isinstance(data.index, pd.DatetimeIndex):
        raise TypeError("data must use a DatetimeIndex")
    if data.index.empty:
        return data.sort_index()
    return data.sort_index()


def _assert_no_leakage(train: pd.DataFrame, val: pd.DataFrame) -> None:
    assert train.index.max() < val.index.min(), "walk-forward leakage detected"


def walk_forward_split(
    data: pd.DataFrame,
    *,
    train_days: int,
    val_days: int,
    step_days: int,
    expanding: bool = False,
) -> Iterator[Fold]:
    """Yield rolling or expanding walk-forward folds with no train/val overlap."""

    ordered = _validate_datetime_index(data)
    if ordered.empty:
        return
    start = pd.Timestamp(ordered.index.min())
    final = pd.Timestamp(ordered.index.max())
    anchor = start
    train_delta = pd.Timedelta(days=train_days)
    val_delta = pd.Timedelta(days=val_days)
    step_delta = pd.Timedelta(days=step_days)

    while True:
        train_start = start if expanding else anchor
        train_end = anchor + train_delta
        val_start = train_end
        val_end = val_start + val_delta
        if val_start > final:
            break
        train = ordered[(ordered.index >= train_start) & (ordered.index < train_end)]
        val = ordered[(ordered.index >= val_start) & (ordered.index < val_end)]
        if not train.empty and not val.empty:
            _assert_no_leakage(train, val)
            yield Fold(
                train_start=pd.Timestamp(train.index.min()),
                train_end=pd.Timestamp(train.index.max()),
                val_start=pd.Timestamp(val.index.min()),
                val_end=pd.Timestamp(val.index.max()),
                train=train,
                val=val,
            )
        anchor = anchor + step_delta
        if anchor + train_delta > final:
            break


class WalkForward:
    def __init__(self, train_days, val_days, step_days, expanding=False):
        self.train_days = train_days
        self.val_days = val_days
        self.step_days = step_days
        self.expanding = expanding

    def split(self, data) -> Iterator[tuple[pd.DataFrame, pd.DataFrame]]:
        for fold in walk_forward_split(
            data,
            train_days=self.train_days,
            val_days=self.val_days,
            step_days=self.step_days,
            expanding=self.expanding,
        ):
            yield fold.train, fold.val


def classify_robustness(train_rank: int, val_rank: int, n: int) -> str:
    half = (n + 1) // 2
    if train_rank == 1 and val_rank == 1:
        return "STRONG ROBUST"
    if train_rank <= half and val_rank <= half:
        return "robust"
    if train_rank <= half and val_rank > half:
        return "OVERFIT (good train, bad val)"
    if train_rank > half and val_rank <= half:
        return "underperformer"
    return "weak both"
