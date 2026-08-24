"""Fixed research-only benchmark configurations."""

from stock_quant.benchmark.momentum import (
    MomentumBenchmarkConfig,
    MomentumBenchmarkResult,
    run_momentum_benchmark,
)
from stock_quant.benchmark.reversal import (
    ReversalBenchmarkResult,
    run_reversal_benchmark,
)

__all__ = [
    "MomentumBenchmarkConfig",
    "MomentumBenchmarkResult",
    "run_momentum_benchmark",
    "ReversalBenchmarkResult",
    "run_reversal_benchmark",
]
