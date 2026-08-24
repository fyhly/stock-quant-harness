"""Immutable standardized research runs."""

from stock_quant.research.run_id import RunId, RunRecord, RunRegistry, RunRegistryError
from stock_quant.research.manifest import (
    create_manifest,
    ExperimentManifest,
    ManifestIntegrityError,
    verify_manifest,
)
from stock_quant.research.artifacts import RunArtifactError, RunArtifacts, RunStore
from stock_quant.research.metrics import (
    MetricInputError,
    StandardMetrics,
    standard_metrics,
)
from stock_quant.research.factor_analytics import (
    DailyFactorAnalytics,
    FactorAnalyticsError,
    FactorPoint,
    QuantileSummary,
    factor_analytics,
)
from stock_quant.research.report import render_html_report

__all__ = [
    "RunId",
    "RunRecord",
    "RunRegistry",
    "RunRegistryError",
    "create_manifest",
    "ExperimentManifest",
    "ManifestIntegrityError",
    "verify_manifest",
    "RunArtifactError",
    "RunArtifacts",
    "RunStore",
    "MetricInputError",
    "StandardMetrics",
    "standard_metrics",
    "DailyFactorAnalytics",
    "FactorAnalyticsError",
    "FactorPoint",
    "QuantileSummary",
    "factor_analytics",
    "render_html_report",
]
