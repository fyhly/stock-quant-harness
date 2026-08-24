"""Deterministic offline daily research report with manual-decision boundary."""

from dataclasses import dataclass
from html import escape
import hashlib
from typing import Mapping, Optional, Tuple

from stock_quant.daily.candidates import DailyCandidateSnapshot
from stock_quant.daily.quality import DailyQualityEvidence
from stock_quant.daily.risk_view import DailyPortfolioResearchView


REQUIRED_IDENTITIES = ("run", "git", "data", "config", "universe", "factor", "risk")


@dataclass(frozen=True)
class DailyResearchReport:
    html: str
    fingerprint: str
    status: str


def render_daily_report(
    *,
    identities: Mapping[str, str],
    quality: DailyQualityEvidence,
    candidates: Optional[DailyCandidateSnapshot],
    risk_view: Optional[DailyPortfolioResearchView],
    failures: Tuple[str, ...],
    limitations: Tuple[str, ...],
) -> DailyResearchReport:
    if set(identities) != set(REQUIRED_IDENTITIES) or any(
        len(value) != 64 for value in identities.values()
    ):
        raise ValueError("all daily report identities are required")
    if quality.passed != (candidates is not None and risk_view is not None):
        raise ValueError("quality state and downstream evidence mismatch")
    status = (
        "RESEARCH_SIGNAL_MANUAL_DECISION_REQUIRED"
        if quality.passed
        else "QUALITY_FAILED_NO_SIGNAL"
    )
    identity_rows = "".join(
        f"<tr><th>{escape(name)}</th><td>{escape(identities[name])}</td></tr>"
        for name in REQUIRED_IDENTITIES
    )
    if candidates is None:
        candidate_rows = "<li>Unavailable because quality failed</li>"
    else:
        candidate_rows = (
            "".join(
                f"<li>{escape(str(item.security_id))}: included={str(item.included).lower()}; "
                f"score={escape(str(item.score))}; reasons={escape('|'.join(item.reasons) or 'NONE')}</li>"
                for item in candidates.candidates
            )
            or "<li>None</li>"
        )

    def items(values: Tuple[str, ...]) -> str:
        return (
            "".join(f"<li>{escape(value)}</li>" for value in values) or "<li>None</li>"
        )

    quality_reasons = quality.fatal_reasons + quality.warnings
    risk_text = (
        "Unavailable"
        if risk_view is None
        else f"RiskDecision; desired turnover={risk_view.desired_turnover}; "
        f"approved turnover={risk_view.approved_turnover}; "
        f"cost reference={risk_view.cost_rate_reference}"
    )
    html = (
        '<!doctype html><html><head><meta charset="utf-8"><title>Daily research</title>'
        "<style>body{font-family:sans-serif}th,td{border:1px solid #888}</style></head><body>"
        "<h1>Daily research report</h1><strong>RESEARCH ONLY — MANUAL DECISION REQUIRED</strong>"
        f"<h2>Status</h2><p>{status}</p><h2>Identities</h2><table>{identity_rows}</table>"
        f"<h2>Quality</h2><ul>{items(quality_reasons)}</ul>"
        f"<h2>Candidates and reasons</h2><ul>{candidate_rows}</ul>"
        f"<h2>Portfolio risk view</h2><p>{escape(risk_text)}</p>"
        f"<h2>Failures</h2><ul>{items(failures)}</ul>"
        f"<h2>Limitations</h2><ul>{items(limitations)}</ul></body></html>"
    )
    return DailyResearchReport(html, hashlib.sha256(html.encode()).hexdigest(), status)
