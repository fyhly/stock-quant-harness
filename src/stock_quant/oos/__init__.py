"""Strictly isolated walk-forward and out-of-sample research."""

from stock_quant.oos.windows import OOSWindowSet, TimeWindow, WindowValidationError
from stock_quant.oos.train import (
    BoundedAccessError,
    FittedArtifact,
    TrainContext,
    TrainRecord,
    run_train,
)
from stock_quant.oos.validation import (
    CandidateEvaluation,
    FrozenSelection,
    ParameterCandidate,
    ValidationContext,
    run_validation,
)
from stock_quant.oos.oos_runner import OOSContext, OOSRecord, run_oos
from stock_quant.oos.walk_forward import (
    WalkForwardResult,
    WalkForwardWindowRecord,
    run_walk_forward,
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
    "CandidateEvaluation",
    "FrozenSelection",
    "ParameterCandidate",
    "ValidationContext",
    "run_validation",
    "OOSContext",
    "OOSRecord",
    "run_oos",
    "WalkForwardResult",
    "WalkForwardWindowRecord",
    "run_walk_forward",
]
