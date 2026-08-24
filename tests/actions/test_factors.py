from datetime import date
from decimal import Decimal

import pytest

from stock_quant.actions import (
    BonusShareEvent,
    build_adjustment_factors,
    CashDividend,
    RightsIssue,
)
from stock_quant.domain import Exchange, SecurityId


SECURITY = SecurityId("600000", Exchange.SHANGHAI)
SOURCE = "a" * 64
ANNOUNCED = date(2024, 1, 1)
RECORD = date(2024, 5, 8)
EX = date(2024, 5, 9)


def same_day_actions() -> tuple[CashDividend, BonusShareEvent, RightsIssue]:
    return (
        CashDividend(
            SECURITY, ANNOUNCED, RECORD, EX, date(2024, 5, 15),
            Decimal("0.3"), SOURCE, "v1"
        ),
        BonusShareEvent(
            SECURITY, ANNOUNCED, RECORD, EX, date(2024, 5, 10),
            Decimal("0.1"), Decimal("0.2"), SOURCE, "v1"
        ),
        RightsIssue(
            SECURITY, ANNOUNCED, RECORD, EX, date(2024, 5, 20),
            Decimal("0.2"), Decimal("8"), SOURCE, "v1"
        ),
    )


def test_same_day_atomic_formula_continuity_and_order_independence() -> None:
    actions = same_day_actions()
    first = build_adjustment_factors(
        SECURITY,
        actions,
        reference_prices={EX: Decimal("10")},
        knowledge_cutoff=EX,
        version="factor-v1",
    )
    reverse = build_adjustment_factors(
        SECURITY,
        reversed(actions),
        reference_prices={EX: Decimal("10")},
        knowledge_cutoff=EX,
        version="factor-v1",
    )
    point = first.points[0]

    expected = (Decimal("10") - Decimal("0.3") + Decimal("0.2") * Decimal("8")) / (
        Decimal(1) + Decimal("0.3") + Decimal("0.2")
    )
    assert point.theoretical_ex_price == expected
    assert point.reference_price * point.ratio == expected
    assert point.event_ids == tuple(sorted(point.event_ids))
    assert first == reverse


def test_knowledge_cutoff_blocks_preannouncement_and_pre_ex_leakage() -> None:
    event = same_day_actions()[0]
    before_announcement = build_adjustment_factors(
        SECURITY,
        [event],
        reference_prices={},
        knowledge_cutoff=date(2023, 12, 31),
        version="v1",
    )
    before_ex = build_adjustment_factors(
        SECURITY,
        [event],
        reference_prices={},
        knowledge_cutoff=date(2024, 5, 8),
        version="v1",
    )

    assert before_announcement.points == ()
    assert before_ex.points == ()


def test_missing_reference_cross_security_and_nonpositive_q_fail() -> None:
    cash = same_day_actions()[0]
    with pytest.raises(ValueError, match="reference"):
        build_adjustment_factors(
            SECURITY, [cash], reference_prices={}, knowledge_cutoff=EX, version="v1"
        )
    with pytest.raises(ValueError, match="requested security"):
        build_adjustment_factors(
            SecurityId("000001", Exchange.SHENZHEN),
            [cash],
            reference_prices={EX: Decimal("10")},
            knowledge_cutoff=EX,
            version="v1",
        )
    huge = CashDividend(
        SECURITY, ANNOUNCED, RECORD, EX, date(2024, 5, 15),
        Decimal("11"), SOURCE, "v1"
    )
    with pytest.raises(ValueError, match="nonpositive"):
        build_adjustment_factors(
            SECURITY,
            [huge],
            reference_prices={EX: Decimal("10")},
            knowledge_cutoff=EX,
            version="v1",
        )


def test_factor_boundaries_are_explicit() -> None:
    series = build_adjustment_factors(
        SECURITY,
        [same_day_actions()[0]],
        reference_prices={EX: Decimal("10")},
        knowledge_cutoff=EX,
        version="v1",
    )
    ratio = series.points[0].ratio

    assert series.forward_factor_for(date(2024, 5, 8)) == ratio
    assert series.forward_factor_for(EX) == 1
    assert series.backward_factor_for(date(2024, 5, 8)) == 1
    assert series.backward_factor_for(EX) == Decimal(1) / ratio
