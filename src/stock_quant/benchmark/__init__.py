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
from stock_quant.benchmark.low_vol import (
    LowVolBenchmarkResult,
    LowVolScore,
    run_low_vol_benchmark,
)
from stock_quant.benchmark.value import ValueBenchmarkResult, run_value_benchmark
from stock_quant.benchmark.quality import QualityBenchmarkResult, run_quality_benchmark
from stock_quant.benchmark.technical import (
    TechnicalBenchmarkResult,
    TechnicalSignal,
    run_technical_benchmarks,
)

__all__ = [
    "MomentumBenchmarkConfig",
    "MomentumBenchmarkResult",
    "run_momentum_benchmark",
    "ReversalBenchmarkResult",
    "run_reversal_benchmark",
    "LowVolBenchmarkResult",
    "LowVolScore",
    "run_low_vol_benchmark",
    "ValueBenchmarkResult",
    "run_value_benchmark",
    "QualityBenchmarkResult",
    "run_quality_benchmark",
    "TechnicalBenchmarkResult",
    "TechnicalSignal",
    "run_technical_benchmarks",
]
