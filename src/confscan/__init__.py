"""Public API for confluence-scanner."""

from confscan.alert.discord import DiscordAlerter
from confscan.alert.telegram import TelegramAlerter
from confscan.backtest.engine import BacktestResult, Trade, run_backtest
from confscan.backtest.metrics import Metrics
from confscan.backtest.regime import RegimeMetrics, classify_regimes, metrics_by_regime
from confscan.backtest.report import (
    BacktestReportSection,
    FoldReportRow,
    RegimeReportRow,
    render_html_report,
)
from confscan.backtest.walk_forward import WalkForward, classify_robustness, walk_forward_split
from confscan.dashboard import DashboardData, ReportLink, ScanRow, render_dashboard, write_dashboard
from confscan.data.binance import funding_rate, klines, long_short_ratio, open_interest
from confscan.data.bybit import funding_rate as bybit_funding_rate
from confscan.score.confluence import ConfluenceResult, ConfluenceScorer, LayerScore
from confscan.signals.funding import funding_frame, funding_percentile
from confscan.signals.ta import (
    adx,
    atr,
    bollinger_bands,
    detect_cross,
    ema,
    ema_cross_signal,
    macd,
    rsi,
)
from confscan.universe.loader import top_n_by_market_cap

__version__ = "0.3.0"

__all__ = [
    "__version__",
    "ema",
    "rsi",
    "macd",
    "bollinger_bands",
    "atr",
    "adx",
    "ema_cross_signal",
    "detect_cross",
    "funding_percentile",
    "funding_frame",
    "bybit_funding_rate",
    "ConfluenceScorer",
    "ConfluenceResult",
    "LayerScore",
    "top_n_by_market_cap",
    "klines",
    "funding_rate",
    "open_interest",
    "long_short_ratio",
    "run_backtest",
    "BacktestResult",
    "Trade",
    "WalkForward",
    "walk_forward_split",
    "classify_robustness",
    "classify_regimes",
    "metrics_by_regime",
    "RegimeMetrics",
    "Metrics",
    "FoldReportRow",
    "RegimeReportRow",
    "BacktestReportSection",
    "render_html_report",
    "DashboardData",
    "ScanRow",
    "ReportLink",
    "render_dashboard",
    "write_dashboard",
    "TelegramAlerter",
    "DiscordAlerter",
]
