"""Monte Carlo robustness helpers for backtest results."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from confscan.backtest.engine import BacktestResult


@dataclass(frozen=True)
class MonteCarloMethod:
    name: str
    final_return_low: float
    final_return_median: float
    final_return_high: float
    max_drawdown_low: float
    max_drawdown_median: float
    max_drawdown_high: float


@dataclass(frozen=True)
class MonteCarloResult:
    simulations: int
    seed: int | None
    confidence: float
    methods: tuple[MonteCarloMethod, ...]


def _drawdown(equity: np.ndarray) -> float:
    peaks = np.maximum.accumulate(equity)
    dd = (equity - peaks) / peaks
    return float(dd.min()) if len(dd) else 0.0


def _trade_returns(result: BacktestResult) -> np.ndarray:
    if result.equity_curve.empty:
        return np.array([], dtype=float)
    values: list[float] = []
    for trade in result.trades:
        try:
            equity_at_entry = float(result.equity_curve.loc[trade.entry_ts])
        except KeyError:
            equity_at_entry = float(result.equity_curve.iloc[0])
        if equity_at_entry > 0:
            values.append(float(trade.pnl) / equity_at_entry)
    if values:
        return np.array(values, dtype=float)
    nonzero = result.returns.dropna().astype(float)
    nonzero = nonzero[nonzero != 0.0]
    return nonzero.to_numpy(dtype=float)


def _summarize(
    name: str,
    samples: np.ndarray,
    *,
    confidence: float,
) -> MonteCarloMethod:
    if samples.size == 0:
        samples = np.zeros((1, 1), dtype=float)
    equity = np.cumprod(1.0 + samples, axis=1)
    equity = np.concatenate([np.ones((equity.shape[0], 1), dtype=float), equity], axis=1)
    final_returns = equity[:, -1] - 1.0
    max_drawdowns = np.array([_drawdown(row) for row in equity], dtype=float)
    tail = (1.0 - confidence) / 2.0
    low_q = tail * 100.0
    high_q = (1.0 - tail) * 100.0
    return MonteCarloMethod(
        name=name,
        final_return_low=float(np.percentile(final_returns, low_q)),
        final_return_median=float(np.percentile(final_returns, 50)),
        final_return_high=float(np.percentile(final_returns, high_q)),
        max_drawdown_low=float(np.percentile(max_drawdowns, low_q)),
        max_drawdown_median=float(np.percentile(max_drawdowns, 50)),
        max_drawdown_high=float(np.percentile(max_drawdowns, high_q)),
    )


def run_monte_carlo(
    result: BacktestResult,
    *,
    simulations: int,
    seed: int | None = None,
    confidence: float = 0.90,
) -> MonteCarloResult:
    """Shuffle and bootstrap backtest trade returns with deterministic seeding."""

    n = max(1, int(simulations))
    trade_returns = _trade_returns(result)
    rng = np.random.default_rng(seed)
    if trade_returns.size == 0:
        shuffle_samples = np.zeros((n, 1), dtype=float)
        bootstrap_samples = np.zeros((n, 1), dtype=float)
    else:
        shuffle_samples = np.vstack([rng.permutation(trade_returns) for _ in range(n)])
        bootstrap_samples = rng.choice(
            trade_returns,
            size=(n, len(trade_returns)),
            replace=True,
        )
    return MonteCarloResult(
        simulations=n,
        seed=seed,
        confidence=float(confidence),
        methods=(
            _summarize("shuffle", shuffle_samples, confidence=confidence),
            _summarize("bootstrap", bootstrap_samples, confidence=confidence),
        ),
    )
