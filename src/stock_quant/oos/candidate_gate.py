"""Predeclared, fail-closed promotion gate for isolated OOS evidence."""

from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
from html import escape
import hashlib
import json
from typing import Tuple

from stock_quant.oos.stability import StabilitySummary


class CandidateDecision(str, Enum):
    REJECT = "REJECT"
    EXPERIMENTAL = "EXPERIMENTAL"
    PROMISING = "PROMISING"
    CANDIDATE = "CANDIDATE"


@dataclass(frozen=True)
class CandidateCriteria:
    minimum_windows: int
    promising_minimum_mean_return: Decimal
    candidate_minimum_mean_return: Decimal
    candidate_maximum_negative_fraction: Decimal

    def __post_init__(self) -> None:
        if (
            self.minimum_windows <= 0
            or self.promising_minimum_mean_return > self.candidate_minimum_mean_return
            or not Decimal(0) <= self.candidate_maximum_negative_fraction <= Decimal(1)
        ):
            raise ValueError("invalid predeclared candidate criteria")

    @property
    def identity(self) -> str:
        raw = json.dumps(
            {
                "minimum_windows": self.minimum_windows,
                "promising_minimum_mean_return": str(
                    self.promising_minimum_mean_return
                ),
                "candidate_minimum_mean_return": str(
                    self.candidate_minimum_mean_return
                ),
                "candidate_maximum_negative_fraction": str(
                    self.candidate_maximum_negative_fraction
                ),
            },
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
        return hashlib.sha256(raw).hexdigest()


@dataclass(frozen=True)
class CandidateEvidence:
    stability: StabilitySummary
    phase14_complete: bool
    contexts_isolated: bool
    selection_frozen_before_oos: bool
    identities_match: bool
    all_windows_reported: bool


@dataclass(frozen=True)
class CandidateGateResult:
    decision: CandidateDecision
    criteria_identity: str
    reasons: Tuple[str, ...]
    research_only: bool = True


def candidate_gate(
    criteria: CandidateCriteria, evidence: CandidateEvidence
) -> CandidateGateResult:
    integrity_reasons: list[str] = []
    checks = (
        (evidence.phase14_complete, "PHASE14_INCOMPLETE"),
        (evidence.contexts_isolated, "OOS_LEAKAGE_OR_CONTEXT_BREACH"),
        (evidence.selection_frozen_before_oos, "SELECTION_NOT_FROZEN"),
        (evidence.identities_match, "IDENTITY_DRIFT"),
        (evidence.all_windows_reported, "INCOMPLETE_WINDOW_EVIDENCE"),
        (evidence.stability.failed_windows == 0, "FAILED_WINDOW"),
        (
            evidence.stability.total_windows
            == evidence.stability.successful_windows
            + evidence.stability.failed_windows,
            "WINDOW_TOTAL_MISMATCH",
        ),
    )
    integrity_reasons.extend(reason for passed, reason in checks if not passed)
    if integrity_reasons:
        return CandidateGateResult(
            CandidateDecision.REJECT, criteria.identity, tuple(integrity_reasons)
        )
    summary = evidence.stability
    if summary.successful_windows < criteria.minimum_windows:
        return CandidateGateResult(
            CandidateDecision.EXPERIMENTAL, criteria.identity, ("INSUFFICIENT_WINDOWS",)
        )
    negative_fraction = Decimal(summary.negative_windows) / Decimal(
        summary.successful_windows
    )
    if (
        summary.mean_oos_return >= criteria.candidate_minimum_mean_return
        and negative_fraction <= criteria.candidate_maximum_negative_fraction
    ):
        return CandidateGateResult(CandidateDecision.CANDIDATE, criteria.identity, ())
    if summary.mean_oos_return >= criteria.promising_minimum_mean_return:
        return CandidateGateResult(
            CandidateDecision.PROMISING,
            criteria.identity,
            ("CANDIDATE_THRESHOLDS_NOT_MET",),
        )
    return CandidateGateResult(
        CandidateDecision.EXPERIMENTAL, criteria.identity, ("PROMISING_RETURN_NOT_MET",)
    )


def render_candidate_report(result: CandidateGateResult) -> str:
    reasons = (
        "".join(f"<li>{escape(reason)}</li>" for reason in result.reasons)
        or "<li>None</li>"
    )
    return (
        '<!doctype html><html><head><meta charset="utf-8"><title>Candidate gate</title>'
        "</head><body><h1>Candidate Gate</h1><strong>RESEARCH ONLY</strong>"
        f"<p>Decision: {escape(result.decision.value)}</p>"
        f"<p>Criteria: {escape(result.criteria_identity)}</p><ul>{reasons}</ul>"
        "</body></html>"
    )
