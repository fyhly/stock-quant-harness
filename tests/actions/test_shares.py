from datetime import date
from decimal import Decimal

import pytest

from stock_quant.actions import (
    apply_bonus_shares,
    BonusShareEvent,
    FractionalSharePolicy,
)
from stock_quant.domain import Exchange, SecurityId


EVENT = BonusShareEvent(
    SecurityId("600000", Exchange.SHANGHAI),
    date(2024, 1, 1),
    date(2024, 5, 8),
    date(2024, 5, 9),
    date(2024, 5, 13),
    Decimal("0.1"),
    Decimal("0.2"),
    "a" * 64,
    "v1",
)


def test_exact_quantity_cost_and_reference_value_conservation() -> None:
    adjustment = apply_bonus_shares(
        EVENT,
        quantity=100,
        total_cost=Decimal("1000"),
        pre_action_reference_price=Decimal("10"),
        application_date=EVENT.share_credit_date,
        fractional_policy=FractionalSharePolicy.REJECT,
    )

    assert adjustment.share_delta == 30
    assert adjustment.new_quantity == 130
    assert adjustment.new_total_cost == adjustment.old_total_cost == Decimal("1000")
    assert adjustment.new_average_cost == Decimal("1000") / Decimal(130)
    assert adjustment.theoretical_post_action_price == Decimal("10") / Decimal("1.3")
    assert adjustment.credited_market_value == adjustment.pre_action_market_value
    assert adjustment.discarded_fraction_value == 0


def test_round_down_records_fractional_conservation_evidence() -> None:
    adjustment = apply_bonus_shares(
        EVENT,
        quantity=101,
        total_cost=Decimal("1000"),
        pre_action_reference_price=Decimal("10"),
        application_date=EVENT.share_credit_date,
        fractional_policy=FractionalSharePolicy.ROUND_DOWN,
    )

    assert adjustment.exact_share_entitlement == Decimal("30.3")
    assert adjustment.share_delta == 30
    assert adjustment.discarded_fraction == Decimal("0.3")
    assert (
        adjustment.credited_market_value + adjustment.discarded_fraction_value
        == adjustment.pre_action_market_value
    )


def test_reject_policy_and_credit_date_boundary_are_explicit() -> None:
    with pytest.raises(ValueError, match="fractional"):
        apply_bonus_shares(
            EVENT,
            quantity=101,
            total_cost=Decimal("1000"),
            pre_action_reference_price=Decimal("10"),
            application_date=EVENT.share_credit_date,
            fractional_policy=FractionalSharePolicy.REJECT,
        )
    with pytest.raises(ValueError, match="share_credit_date"):
        apply_bonus_shares(
            EVENT,
            quantity=100,
            total_cost=Decimal("1000"),
            pre_action_reference_price=Decimal("10"),
            application_date=EVENT.ex_date,
            fractional_policy=FractionalSharePolicy.ROUND_DOWN,
        )


def test_fractional_policy_cannot_be_implicit() -> None:
    with pytest.raises(TypeError, match="explicitly"):
        apply_bonus_shares(
            EVENT,
            quantity=100,
            total_cost=Decimal("1000"),
            pre_action_reference_price=Decimal("10"),
            application_date=EVENT.share_credit_date,
            fractional_policy="ROUND_DOWN",  # type: ignore[arg-type]
        )
