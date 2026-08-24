from dataclasses import replace
from datetime import date
from decimal import Decimal

import pytest

from stock_quant.oos.train import FittedArtifact
from stock_quant.oos.validation import ParameterCandidate, run_validation
from stock_quant.oos.oos_runner import run_oos
from stock_quant.oos.windows import OOSWindowSet, TimeWindow


WINDOWS = OOSWindowSet.create(
    TimeWindow(date(2024, 1, 1), date(2024, 1, 3)),
    TimeWindow(date(2024, 1, 3), date(2024, 1, 5)),
    TimeWindow(date(2024, 1, 5), date(2024, 1, 7)),
)
FITTED = FittedArtifact(b"fit", b"base", "a" * 64, "b" * 64)
SELECTION = run_validation(
    WINDOWS,
    {},
    FITTED,
    (ParameterCandidate("fixed", b"cfg"),),
    lambda _context, _candidate: Decimal(1),
)


def test_oos_uses_only_frozen_config_and_repeats_exactly() -> None:
    data = {date(2024, 1, 5): b"result"}

    def execute(context, config):  # type: ignore[no-untyped-def]
        return context.get(date(2024, 1, 5)) + config

    first = run_oos(WINDOWS, data, SELECTION, execute)
    assert first == run_oos(WINDOWS, data, SELECTION, execute) and first.succeeded
    assert first.selected_candidate_id == "fixed" and first.result == b"resultcfg"


def test_future_access_and_selection_identity_drift_fail_closed() -> None:
    failure = run_oos(
        WINDOWS, {}, SELECTION, lambda context, _config: context.get(date(2024, 1, 7))
    )
    assert not failure.succeeded and failure.failure_type == "BoundedAccessError"
    with pytest.raises(ValueError, match="config identity drift"):
        run_oos(
            WINDOWS,
            {},
            replace(SELECTION, selected_config=b"changed"),
            lambda _context, _config: b"",
        )
