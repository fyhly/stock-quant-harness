"""Frozen offline real-data research pipeline."""

from stock_quant.e2e.real_pipeline import (
    build_real_universe,
    compute_real_features,
    load_real_bars,
    RealFeatureClosure,
    RealFeatureRow,
)

__all__ = [
    "build_real_universe",
    "compute_real_features",
    "load_real_bars",
    "RealFeatureClosure",
    "RealFeatureRow",
]
