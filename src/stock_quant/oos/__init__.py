"""Strictly isolated walk-forward and out-of-sample research."""

from stock_quant.oos.windows import OOSWindowSet, TimeWindow, WindowValidationError
from stock_quant.oos.train import (
    BoundedAccessError,
    FittedArtifact,
    TrainContext,
    TrainRecord,
    run_train,
)

__all__ = [
    "OOSWindowSet",
    "TimeWindow",
    "WindowValidationError",
    "BoundedAccessError",
    "FittedArtifact",
    "TrainContext",
    "TrainRecord",
    "run_train",
]
