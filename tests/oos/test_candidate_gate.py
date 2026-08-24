from dataclasses import replace
from decimal import Decimal

from stock_quant.oos.candidate_gate import (
    CandidateCriteria,
    CandidateDecision,
    CandidateEvidence,
    candidate_gate,
    render_candidate_report,
)
from stock_quant.oos.stability import StabilityWindow, stability_summary


CRITERIA = CandidateCriteria(2, Decimal(0), Decimal(".05"), Decimal(".5"))
SUMMARY = stability_summary(
    (
        StabilityWindow("a", "p", Decimal(".1"), ()),
        StabilityWindow("b", "p", Decimal(".2"), ()),
    )
)
EVIDENCE = CandidateEvidence(SUMMARY, True, True, True, True, True)


def test_deterministic_predeclared_candidate_and_research_only_report() -> None:
    result = candidate_gate(CRITERIA, EVIDENCE)
    assert result == candidate_gate(CRITERIA, EVIDENCE)
    assert result.decision is CandidateDecision.CANDIDATE and not result.reasons
    report = render_candidate_report(result)
    assert "RESEARCH ONLY" in report and "CANDIDATE" in report
    assert "http://" not in report and "https://" not in report


def test_pre_phase_leakage_failure_identity_and_incomplete_evidence_reject() -> None:
    mutations = (
        (
            CandidateEvidence(SUMMARY, False, True, True, True, True),
            "PHASE14_INCOMPLETE",
        ),
        (CandidateEvidence(SUMMARY, True, False, True, True, True), "OOS_LEAKAGE"),
        (
            CandidateEvidence(SUMMARY, True, True, False, True, True),
            "SELECTION_NOT_FROZEN",
        ),
        (CandidateEvidence(SUMMARY, True, True, True, False, True), "IDENTITY_DRIFT"),
        (
            CandidateEvidence(SUMMARY, True, True, True, True, False),
            "INCOMPLETE_WINDOW_EVIDENCE",
        ),
    )
    for evidence, reason in mutations:
        result = candidate_gate(CRITERIA, evidence)
        assert result.decision is CandidateDecision.REJECT
        assert any(reason in item for item in result.reasons)
    failed = stability_summary((StabilityWindow("a", "", None, (), "OOS", "bad"),))
    assert (
        candidate_gate(CRITERIA, replace(EVIDENCE, stability=failed)).decision
        is CandidateDecision.REJECT
    )


def test_experimental_and_promising_are_deterministic_non_candidate_states() -> None:
    one = stability_summary((StabilityWindow("a", "p", Decimal(".1"), ()),))
    assert (
        candidate_gate(CRITERIA, replace(EVIDENCE, stability=one)).decision
        is CandidateDecision.EXPERIMENTAL
    )
    weak = stability_summary(
        (
            StabilityWindow("a", "p", Decimal(".01"), ()),
            StabilityWindow("b", "p", Decimal(".01"), ()),
        )
    )
    assert (
        candidate_gate(CRITERIA, replace(EVIDENCE, stability=weak)).decision
        is CandidateDecision.PROMISING
    )
