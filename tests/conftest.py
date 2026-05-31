from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest


@pytest.fixture
def sample_ohlcv() -> pd.DataFrame:
    path = Path(__file__).parent / "fixtures" / "btc_4h_sample.csv"
    df = pd.read_csv(path, parse_dates=["timestamp"])
    return df.set_index("timestamp")


@pytest.fixture
def tiny_ohlcv() -> pd.DataFrame:
    index = pd.date_range("2024-01-01", periods=8, freq="4h", tz="UTC")
    return pd.DataFrame(
        {
            "open": [100, 101, 102, 103, 104, 105, 106, 107],
            "high": [101, 103, 104, 105, 106, 107, 108, 109],
            "low": [99, 100, 101, 102, 103, 104, 105, 106],
            "close": [100, 102, 103, 104, 105, 106, 107, 108],
            "volume": [10, 11, 12, 13, 14, 15, 16, 17],
        },
        index=index,
    )
