"""Frozen offline real-data research pipeline."""

from stock_quant.e2e.real_pipeline import (
    build_real_universe,
    build_real_allocation,
    compute_real_features,
    load_real_bars,
    RealFeatureClosure,
    RealFeatureRow,
    RealAllocationClosure,
)

__all__ = [
    "build_real_universe",
    "build_real_allocation",
    "compute_real_features",
    "load_real_bars",
    "RealFeatureClosure",
    "RealFeatureRow",
    "RealAllocationClosure",
]
