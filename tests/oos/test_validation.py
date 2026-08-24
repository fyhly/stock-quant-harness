from datetime import date
from decimal import Decimal

from stock_quant.oos.train import FittedArtifact
from stock_quant.oos.validation import ParameterCandidate, run_validation
from stock_quant.oos.windows import OOSWindowSet, TimeWindow


WINDOWS = OOSWindowSet.create(
    TimeWindow(date(2024, 1, 1), date(2024, 1, 3)),
    TimeWindow(date(2024, 1, 3), date(2024, 1, 5)),
    TimeWindow(date(2024, 1, 5), date(2024, 1, 7)),
)
FITTED = FittedArtifact(b"fit", b"base", "a" * 64, "b" * 64)


def test_fixed_space_complete_audit_and_deterministic_tie_selection() -> None:
    candidates = (
        ParameterCandidate("b", b"2"),
        ParameterCandidate("a", b"1"),
        ParameterCandidate("bad", b"3"),
    )

    def evaluate(context, candidate):  # type: ignore[no-untyped-def]
        context.get(date(2024, 1, 3))
        if candidate.candidate_id == "bad":
            raise RuntimeError("retained")
        return Decimal(1)

    first = run_validation(WINDOWS, {date(2024, 1, 3): 1}, FITTED, candidates, evaluate)
    second = run_validation(
        WINDOWS, {date(2024, 1, 3): 1}, FITTED, tuple(reversed(candidates)), evaluate
    )
    assert first == second and first.selected_candidate_id == "a"
    assert (
        len(first.evaluations) == 3
        and sum(not item.succeeded for item in first.evaluations) == 1
    )


def test_validation_context_rejects_train_and_oos_access_and_retains_failures() -> None:
    candidates = (
        ParameterCandidate("train-leak", b"1"),
        ParameterCandidate("oos-leak", b"2"),
        ParameterCandidate("valid", b"3"),
    )

    def evaluate(context, candidate):  # type: ignore[no-untyped-def]
        if candidate.candidate_id == "train-leak":
            return Decimal(context.get(date(2024, 1, 2)))
        if candidate.candidate_id == "oos-leak":
            return Decimal(context.get(date(2024, 1, 5)))
        return Decimal(0)

    result = run_validation(WINDOWS, {}, FITTED, candidates, evaluate)
    assert result.selected_candidate_id == "valid"
    assert tuple(item.failure_type for item in result.evaluations[:2]) == (
        "BoundedAccessError",
        "BoundedAccessError",
    )
