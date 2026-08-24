"""Deterministic point-in-time market-wide research primitives."""

from stock_quant.market_research.universe_gate import (
    MarketUniverseGateError,
    MarketUniverseGateEvidence,
    evaluate_market_universe,
)
from stock_quant.market_research.runner import (
    MarketBatchResult,
    MarketItemRecord,
    MarketWorkItem,
    run_cross_sectional_batch,
)
from stock_quant.market_research.ic import MarketICSummary, market_ic_summary
from stock_quant.market_research.quantiles import QuantilePortfolio, quantile_backtests
from stock_quant.market_research.exposure import (
    ExposureAnalyticsError,
    ExposureAttribution,
    ExposurePoint,
    exposure_attribution,
)

__all__ = [
    "MarketUniverseGateError",
    "MarketUniverseGateEvidence",
    "evaluate_market_universe",
    "MarketBatchResult",
    "MarketItemRecord",
    "MarketWorkItem",
    "run_cross_sectional_batch",
    "MarketICSummary",
    "market_ic_summary",
    "QuantilePortfolio",
    "quantile_backtests",
    "ExposureAnalyticsError",
    "ExposureAttribution",
    "ExposurePoint",
    "exposure_attribution",
]
