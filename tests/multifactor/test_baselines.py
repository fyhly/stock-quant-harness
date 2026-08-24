from datetime import date
from decimal import Decimal

import pytest

from stock_quant.domain import SecurityId
from stock_quant.multifactor.baselines import (
    BaselineAllocationError,
    baseline_allocators,
)
from stock_quant.multifactor.neutralize import NeutralizedScore


def row(code: str, value: str, day: int = 2) -> NeutralizedScore:
    exchange = "XSHE" if code.startswith("0") else "XSHG"
    return NeutralizedScore(
        date(2024, 1, day),
        SecurityId.parse(f"{code}.{exchange}"),
        "I",
        Decimal(1),
        Decimal(value),
        Decimal(value),
        Decimal(value),
        "v1",
        "T:v1",
        "a" * 64,
    )


def test_top_n_selection_weights_precision_candidates_and_determinism() -> None:
    rows = (row("600000", "2"), row("000001", "3"), row("000002", "1"))
    first = baseline_allocators(
        rows, top_n=2, cash_target=Decimal(".1"), quantum=Decimal(".0001")
    )
    second = baseline_allocators(
        reversed(rows), top_n=2, cash_target=Decimal(".1"), quantum=Decimal(".0001")
    )
    assert first == second and tuple(item.name for item in first) == (
        "TOP_N_EQUAL",
        "TOP_N_SHIFTED_SCORE",
    )
    assert first[0].selected_ids == ("000001.XSHE", "600000.XSHG")
    for candidate in first:
        assert (
            sum(
                (item.weight for item in candidate.portfolio.weights),
                candidate.portfolio.cash_weight,
            )
            == 1
        )
        assert len(candidate.config_identity) == 64


def test_invalid_top_n_duplicate_and_cross_date_fail() -> None:
    with pytest.raises(BaselineAllocationError, match="top_n"):
        baseline_allocators(
            (row("000001", "1"),),
            top_n=2,
            cash_target=Decimal(0),
            quantum=Decimal(".01"),
        )
    with pytest.raises(BaselineAllocationError, match="unique date"):
        baseline_allocators(
            (row("000001", "1", 2), row("600000", "2", 3)),
            top_n=1,
            cash_target=Decimal(0),
            quantum=Decimal(".01"),
        )
