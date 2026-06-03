"""Pure-pandas technical analysis primitives."""

from __future__ import annotations

import numpy as np
import pandas as pd


def ema(series: pd.Series, period: int) -> pd.Series:
    return series.astype(float).ewm(span=period, adjust=False).mean()


def _true_range(df: pd.DataFrame) -> pd.Series:
    high = df["high"].astype(float)
    low = df["low"].astype(float)
    close = df["close"].astype(float)
    prev_close = close.shift(1)
    return pd.concat(
        [(high - low), (high - prev_close).abs(), (low - prev_close).abs()],
        axis=1,
    ).max(axis=1)


def detect_cross(fast: pd.Series, slow: pd.Series) -> pd.Series:
    """Return +1 for bullish crosses, -1 for bearish crosses, and 0 otherwise."""

    prev_fast = fast.shift(1)
    prev_slow = slow.shift(1)
    bull = (prev_fast <= prev_slow) & (fast > slow)
    bear = (prev_fast >= prev_slow) & (fast < slow)
    out = pd.Series(0, index=fast.index, dtype="int64")
    out.loc[bull.fillna(False)] = 1
    out.loc[bear.fillna(False)] = -1
    return out


def ema_cross_signal(
    df: pd.DataFrame,
    *,
    fast: int,
    slow: int,
    trend: int,
    use_forming_bar: bool = False,
) -> dict:
    """Evaluate EMA-cross features on the last closed bar by default."""

    required = {"open", "high", "low", "close", "volume"}
    missing = required - set(df.columns)
    if missing:
        return {"valid": False, "reason": f"missing_columns:{','.join(sorted(missing))}"}
    min_bars = max(fast, slow, trend) + 5
    if len(df) < min_bars:
        return {"valid": False, "reason": "insufficient_history"}

    work = df.copy()
    work["ema_fast"] = ema(work["close"], fast)
    work["ema_slow"] = ema(work["close"], slow)
    work["ema_trend"] = ema(work["close"], trend)
    work["atr"] = atr(work, 14)
    work["adx"] = adx(work, 14)

    i_last, i_prev = (-1, -2) if use_forming_bar else (-2, -3)
    last = work.iloc[i_last]
    prev = work.iloc[i_prev]

    cross_up = bool(prev["ema_fast"] <= prev["ema_slow"] and last["ema_fast"] > last["ema_slow"])
    above_trend = bool(last["close"] > last["ema_trend"])

    trend_pos = len(work) + i_last - 20 >= 0
    if trend_pos:
        ema_then = float(work["ema_trend"].iloc[i_last - 20])
        ema_now = float(work["ema_trend"].iloc[i_last])
        trend_slope = (ema_now - ema_then) / ema_then if ema_then else 0.0
    else:
        trend_slope = 0.0

    vol_window = work["volume"].iloc[i_last - 20 : i_last]
    vol_avg = float(vol_window.mean()) if len(vol_window) else 0.0
    vol_confirm = bool(vol_avg > 0 and float(last["volume"]) > 1.2 * vol_avg)

    ema_fast = float(last["ema_fast"])
    stretch = (float(last["close"]) - ema_fast) / ema_fast if ema_fast else 0.0
    stretch_ok = bool(stretch <= 0.25)

    atr_value = float(last["atr"]) if not pd.isna(last["atr"]) else 0.0
    atr_pct = atr_value / float(last["close"]) if float(last["close"]) else 0.0
    adx_value = float(last["adx"]) if not pd.isna(last["adx"]) else 0.0

    if use_forming_bar:
        entry_price = float(last["close"])
        entry_time = work.index[i_last]
    else:
        entry_bar = work.iloc[i_last + 1]
        entry_price = float(entry_bar["open"])
        entry_time = work.index[i_last + 1]

    return {
        "valid": True,
        "cross_up": cross_up,
        "above_trend": above_trend,
        "trend_slope": float(trend_slope),
        "trend_slope_pos": bool(trend_slope > 0),
        "vol_confirm": vol_confirm,
        "stretch": float(stretch),
        "stretch_ok": stretch_ok,
        "last_close": float(last["close"]),
        "last_time": pd.Timestamp(work.index[i_last]).isoformat(),
        "entry_price": entry_price,
        "entry_time": pd.Timestamp(entry_time).isoformat(),
        "atr_pct": float(atr_pct),
        "atr": atr_value,
        "adx": adx_value,
        "ema_fast": ema_fast,
        "ema_slow": float(last["ema_slow"]),
        "ema_trend": float(last["ema_trend"]),
        "signal_bar_idx": i_last,
    }


def rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.astype(float).diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    avg_loss = loss.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    return (100 - (100 / (1 + rs))).fillna(50.0)


def macd(
    series: pd.Series,
    fast: int = 12,
    slow: int = 26,
    signal: int = 9,
) -> tuple[pd.Series, pd.Series, pd.Series]:
    macd_line = ema(series, fast) - ema(series, slow)
    signal_line = ema(macd_line, signal)
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram


def bollinger_bands(
    series: pd.Series,
    period: int = 20,
    std_dev: float = 2.0,
) -> tuple[pd.Series, pd.Series, pd.Series]:
    middle = series.astype(float).rolling(period, min_periods=period).mean()
    spread = series.astype(float).rolling(period, min_periods=period).std(ddof=0)
    upper = middle + std_dev * spread
    lower = middle - std_dev * spread
    return lower, middle, upper


def atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    true_range = _true_range(df)
    return true_range.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()


def adx(df: pd.DataFrame, period: int = 14) -> pd.Series:
    high = df["high"].astype(float)
    low = df["low"].astype(float)

    up_move = high.diff()
    down_move = -low.diff()
    plus_dm = pd.Series(
        np.where((up_move > down_move) & (up_move > 0), up_move, 0.0),
        index=df.index,
        dtype=float,
    )
    minus_dm = pd.Series(
        np.where((down_move > up_move) & (down_move > 0), down_move, 0.0),
        index=df.index,
        dtype=float,
    )

    smoothed_atr = _true_range(df).ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    plus_di = (
        100
        * plus_dm.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
        / smoothed_atr.replace(0, np.nan)
    )
    minus_di = (
        100
        * minus_dm.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
        / smoothed_atr.replace(0, np.nan)
    )
    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan)
    return dx.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
