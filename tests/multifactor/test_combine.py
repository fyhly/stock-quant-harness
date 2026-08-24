from datetime import date
from decimal import Decimal

import pytest

from stock_quant.domain import SecurityId
from stock_quant.multifactor.combine import (
    FactorCombinationError,
    FactorInput,
    FactorMissingPolicy,
    FactorSpec,
    combine_factors,
)


A, B = SecurityId.parse("000001.XSHE"), SecurityId.parse("600000.XSHG")
SPECS = (
    FactorSpec("momentum", Decimal(2), "a" * 64),
    FactorSpec("value", Decimal(-1), "b" * 64),
)


def row(day: int, security: SecurityId, momentum, value):  # type: ignore[no-untyped-def]
    return FactorInput(
        date(2024, 1, day), security, (("momentum", momentum), ("value", value))
    )


def test_weights_signs_lineage_order_constants_and_dates_are_isolated() -> None:
    rows = (
        row(3, A, Decimal(1), Decimal(1)),
        row(2, B, Decimal(2), Decimal(1)),
        row(2, A, Decimal(2), Decimal(1)),
    )
    result = combine_factors(
        rows, reversed(SPECS), missing_policy=FactorMissingPolicy.REJECT
    )
    assert tuple((item.as_of, item.security_id) for item in result) == tuple(
        sorted((r.as_of, r.security_id) for r in rows)
    )
    assert tuple(item.score for item in result) == (Decimal(3), Decimal(3), Decimal(1))
    assert all(
        item.lineage == (("momentum", "a" * 64), ("value", "b" * 64)) for item in result
    )


def test_missing_and_alignment_policies_are_explicit() -> None:
    missing = row(2, A, None, Decimal(1))
    with pytest.raises(FactorCombinationError, match="missing"):
        combine_factors((missing,), SPECS, missing_policy=FactorMissingPolicy.REJECT)
    assert (
        combine_factors((missing,), SPECS, missing_policy=FactorMissingPolicy.ZERO)[
            0
        ].score
        == -1
    )
    misaligned = FactorInput(
        date(2024, 1, 2), A, (("value", Decimal(1)), ("momentum", Decimal(1)))
    )
    with pytest.raises(FactorCombinationError, match="aligned"):
        combine_factors((misaligned,), SPECS, missing_policy=FactorMissingPolicy.REJECT)
