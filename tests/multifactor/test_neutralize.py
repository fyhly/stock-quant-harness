from datetime import date
from decimal import Decimal

import pytest

from stock_quant.domain import SecurityId
from stock_quant.multifactor.combine import CompositeScore, FactorMissingPolicy
from stock_quant.multifactor.neutralize import NeutralizationError, neutralize_scores
from stock_quant.universe import (
    IndustryMembership,
    IndustryMembershipHistory,
    IndustryTaxonomy,
)


A, B, C = (
    SecurityId.parse("000001.XSHE"),
    SecurityId.parse("000002.XSHE"),
    SecurityId.parse("600000.XSHG"),
)
TAX = IndustryTaxonomy("CITICS", "v1")


def score(day: date, security: SecurityId, value: str) -> CompositeScore:
    return CompositeScore(
        day, security, Decimal(value), (), (), FactorMissingPolicy.REJECT
    )


def history() -> IndustryMembershipHistory:
    return IndustryMembershipHistory(
        TAX,
        (
            IndustryMembership(TAX, A, "OLD", date(2020, 1, 1), date(2024, 1, 3)),
            IndustryMembership(TAX, A, "NEW", date(2024, 1, 3)),
            IndustryMembership(TAX, B, "BANK", date(2020, 1, 1)),
            IndustryMembership(TAX, C, "BANK", date(2020, 1, 1)),
        ),
    )


def test_pit_industry_change_and_daily_only_size_fit() -> None:
    d1, d2 = date(2024, 1, 2), date(2024, 1, 3)
    rows = (
        score(d1, A, "10"),
        score(d1, B, "1"),
        score(d1, C, "3"),
        score(d2, A, "20"),
        score(d2, B, "2"),
        score(d2, C, "4"),
    )
    sizes = {
        (day, security): Decimal(index)
        for day in (d1, d2)
        for index, security in enumerate((A, B, C), 1)
    }
    result = neutralize_scores(rows, history(), sizes, size_identity="a" * 64)
    assert tuple(item.industry_code for item in result) == (
        "OLD",
        "BANK",
        "BANK",
        "NEW",
        "BANK",
        "BANK",
    )
    assert tuple(item.as_of for item in result[:3]) == (d1, d1, d1)
    assert all(item.taxonomy_identity == "CITICS:v1" for item in result)


def test_gap_missing_size_and_singular_constant_extreme_cases() -> None:
    day = date(2024, 1, 2)
    rows = (score(day, B, "1E+20"), score(day, C, "1E+20"))
    sizes = {(day, B): Decimal(1), (day, C): Decimal(1)}
    result = neutralize_scores(rows, history(), sizes, size_identity="a" * 64)
    assert all(item.residual_score == 0 for item in result)
    with pytest.raises(NeutralizationError, match="size"):
        neutralize_scores(rows, history(), {}, size_identity="a" * 64)
    missing_history = IndustryMembershipHistory(TAX, ())
    with pytest.raises(NeutralizationError, match="PIT"):
        neutralize_scores(
            (score(day, A, "1"),),
            missing_history,
            {(day, A): Decimal(1)},
            size_identity="a" * 64,
        )
