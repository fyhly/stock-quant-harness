"""Offline, fail-closed daily research workflow."""

from stock_quant.daily.update import DailyDataUpdate, DailyUpdateError, run_daily_update
from stock_quant.daily.quality import (
    DailyQualityConfig,
    DailyQualityEvidence,
    DailyQualityFailure,
    DailyQualitySample,
    evaluate_daily_quality,
    invoke_after_quality,
)
from stock_quant.daily.universe_refresh import refresh_daily_universe
from stock_quant.daily.factors import (
    DailyFactorFailure,
    DailyFactorRow,
    DailyFactorSnapshot,
    refresh_daily_factors,
)
from stock_quant.daily.candidates import (
    DailyCandidate,
    DailyCandidateSnapshot,
    generate_daily_candidates,
)
from stock_quant.daily.risk_view import (
    DailyPortfolioResearchView,
    generate_portfolio_risk_view,
)
from stock_quant.daily.report import DailyResearchReport, render_daily_report

__all__ = ["DailyDataUpdate", "DailyUpdateError", "run_daily_update"]
__all__ += [
    "DailyQualityConfig",
    "DailyQualityEvidence",
    "DailyQualityFailure",
    "DailyQualitySample",
    "evaluate_daily_quality",
    "invoke_after_quality",
    "refresh_daily_universe",
    "DailyFactorFailure",
    "DailyFactorRow",
    "DailyFactorSnapshot",
    "refresh_daily_factors",
    "DailyCandidate",
    "DailyCandidateSnapshot",
    "generate_daily_candidates",
    "DailyPortfolioResearchView",
    "generate_portfolio_risk_view",
    "DailyResearchReport",
    "render_daily_report",
]
