"""Point-in-time feature and factor primitives."""

from stock_quant.features.api import (
    build_feature_result,
    FeatureContractError,
    FeatureObservation,
    FeatureRequest,
    FeatureResult,
    FeatureScope,
)
from stock_quant.features.momentum import PriceObservation, trailing_return
from stock_quant.features.reversal import short_term_reversal
from stock_quant.features.volatility import (
    MissingReturnPolicy,
    trailing_volatility,
    VolatilityResult,
)

__all__ = [
    "build_feature_result",
    "FeatureContractError",
    "FeatureObservation",
    "FeatureRequest",
    "FeatureResult",
    "FeatureScope",
    "PriceObservation",
    "MissingReturnPolicy",
    "short_term_reversal",
    "trailing_return",
    "trailing_volatility",
    "VolatilityResult",
]
