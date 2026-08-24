"""Deterministic point-in-time market-wide research primitives."""

from stock_quant.market_research.universe_gate import (
    MarketUniverseGateError,
    MarketUniverseGateEvidence,
    evaluate_market_universe,
)

__all__ = [
    "MarketUniverseGateError",
    "MarketUniverseGateEvidence",
    "evaluate_market_universe",
]
