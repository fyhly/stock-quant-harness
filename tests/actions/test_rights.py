from datetime import date
from decimal import Decimal

import pytest

from stock_quant.actions import (
    apply_rights_issue,
    FractionalSharePolicy,
    RightsElection,
    RightsIssue,
)
from stock_quant.domain import Exchange, SecurityId


EVENT = RightsIssue(
    SecurityId("600000", Exchange.SHANGHAI),
    date(2024, 1, 1),
    date(2024, 5, 8),
    date(2024, 5, 9),
    date(2024, 5, 20),
    Decimal("0.2"),
    Decimal("8"),
    "a" * 64,
    "v1",
)


def test_explicit_participation_changes_cash_shares_and_cost() -> None:
    adjustment = apply_rights_issue(
        EVENT,
        quantity=100,
        total_cost=Decimal("1000"),
        available_cash=Decimal("500"),
        application_date=EVENT.settlement_date,
        election=RightsElection.PARTICIPATE,
        fractional_policy=FractionalSharePolicy.REJECT,
    )

    assert adjustment.share_delta == 20
    assert adjustment.new_quantity == 120
    assert adjustment.cash_delta == Decimal("-160")
    assert adjustment.new_total_cost == Decimal("1160")


def test_explicit_decline_has_no_cash_share_or_cost_delta() -> None:
    adjustment = apply_rights_issue(
        EVENT,
        quantity=101,
        total_cost=Decimal("1000"),
        available_cash=Decimal(0),
        application_date=EVENT.settlement_date,
        election=RightsElection.DECLINE,
        fractional_policy=FractionalSharePolicy.ROUND_DOWN,
    )

    assert adjustment.exact_share_entitlement == Decimal("20.2")
    assert adjustment.share_delta == 0
    assert adjustment.cash_delta == 0
    assert adjustment.new_total_cost == adjustment.old_total_cost


def test_insufficient_cash_and_settlement_boundary_fail() -> None:
    with pytest.raises(ValueError, match="insufficient cash"):
        apply_rights_issue(
            EVENT,
            quantity=100,
            total_cost=Decimal("1000"),
            available_cash=Decimal("159.99"),
            application_date=EVENT.settlement_date,
            election=RightsElection.PARTICIPATE,
            fractional_policy=FractionalSharePolicy.REJECT,
        )
    with pytest.raises(ValueError, match="settlement_date"):
        apply_rights_issue(
            EVENT,
            quantity=100,
            total_cost=Decimal("1000"),
            available_cash=Decimal("500"),
            application_date=EVENT.ex_date,
            election=RightsElection.PARTICIPATE,
            fractional_policy=FractionalSharePolicy.REJECT,
        )


def test_fractional_and_election_policies_are_never_implicit() -> None:
    with pytest.raises(ValueError, match="fractional"):
        apply_rights_issue(
            EVENT,
            quantity=101,
            total_cost=Decimal("1000"),
            available_cash=Decimal("500"),
            application_date=EVENT.settlement_date,
            election=RightsElection.PARTICIPATE,
            fractional_policy=FractionalSharePolicy.REJECT,
        )
    with pytest.raises(TypeError, match="election"):
        apply_rights_issue(
            EVENT,
            quantity=100,
            total_cost=Decimal("1000"),
            available_cash=Decimal("500"),
            application_date=EVENT.settlement_date,
            election="PARTICIPATE",  # type: ignore[arg-type]
            fractional_policy=FractionalSharePolicy.REJECT,
        )
