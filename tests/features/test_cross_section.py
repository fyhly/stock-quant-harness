from datetime import date
from decimal import Decimal

import pytest

from stock_quant.domain import Exchange, SecurityId, TradingDay
from stock_quant.features import (
    CrossSectionResult,
    CrossSectionValue,
    cross_sectional_transform,
    FeatureContractError,
    MissingPolicy,
)


DAY = TradingDay(date(2024, 1, 2))
IDS = tuple(
    SecurityId(code, Exchange.SHANGHAI)
    for code in ("600000", "600001", "600002", "600003")
)


def transform(
    rows: tuple[CrossSectionValue, ...], policy: MissingPolicy = MissingPolicy.KEEP
) -> CrossSectionResult:
    return cross_sectional_transform(
        rows,
        lower_quantile=Decimal("0.25"),
        upper_quantile=Decimal("0.75"),
        missing_policy=policy,
    )


def test_outliers_ties_missing_and_input_order_are_deterministic() -> None:
    rows = tuple(
        CrossSectionValue(security, DAY, value)
        for security, value in zip(IDS, (Decimal(1), Decimal(1), Decimal(2), None))
    )
    first = transform(rows)
    second = transform(tuple(reversed(rows)))
    assert first == second
    assert first.fitted_day == DAY
    assert first.values[0].rank == first.values[1].rank
    assert first.values[-1].standardized is None
    assert transform(rows, MissingPolicy.DROP).values[-1].security_id == IDS[2]


def test_constant_cross_section_and_cross_date_fit_boundary() -> None:
    constant = transform(
        tuple(CrossSectionValue(security, DAY, Decimal(5)) for security in IDS)
    )
    assert all(row.standardized == 0 for row in constant.values)
    mixed = (
        CrossSectionValue(IDS[0], DAY, Decimal(1)),
        CrossSectionValue(IDS[1], TradingDay(date(2024, 1, 3)), Decimal(2)),
    )
    with pytest.raises(FeatureContractError, match="one date"):
        transform(mixed)
    with pytest.raises(FeatureContractError, match="missing"):
        transform((CrossSectionValue(IDS[0], DAY, None),), MissingPolicy.REJECT)
