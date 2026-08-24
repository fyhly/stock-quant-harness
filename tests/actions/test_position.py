from datetime import date
from decimal import Decimal

import pytest

from stock_quant.actions import (
    apply_bonus_to_position,
    apply_rights_to_position,
    BonusShareEvent,
    calculate_cash_entitlement,
    CashDividend,
    DuplicateActionApplicationError,
    FlatDividendTaxPolicy,
    FractionalSharePolicy,
    PositionState,
    recognize_dividend_entitlement,
    RightsElection,
    RightsIssue,
    settle_dividend_receivable,
)
from stock_quant.domain import Exchange, SecurityId


SECURITY = SecurityId("600000", Exchange.SHANGHAI)
SOURCE = "a" * 64
ANNOUNCE = date(2024, 1, 1)
RECORD = date(2024, 5, 8)
EX = date(2024, 5, 9)


def events() -> tuple[CashDividend, BonusShareEvent, RightsIssue]:
    return (
        CashDividend(
            SECURITY, ANNOUNCE, RECORD, EX, EX, Decimal("0.3"), SOURCE, "v1"
        ),
        BonusShareEvent(
            SECURITY, ANNOUNCE, RECORD, EX, EX,
            Decimal("0.1"), Decimal("0.2"), SOURCE, "v1"
        ),
        RightsIssue(
            SECURITY, ANNOUNCE, RECORD, EX, EX,
            Decimal("0.2"), Decimal("8"), SOURCE, "v1"
        ),
    )


def test_ordered_multi_action_nav_and_accounting_continuity() -> None:
    dividend, bonus, rights = events()
    state = PositionState(SECURITY, 100, Decimal("1000"), Decimal("1000"))
    pre_nav = state.nav(Decimal("10"))
    entitlement = calculate_cash_entitlement(
        dividend, eligible_quantity=100, as_of=RECORD,
        tax_policy=FlatDividendTaxPolicy("zero-tax-v1", Decimal(0))
    )
    state = recognize_dividend_entitlement(state, entitlement, application_date=EX)
    state = apply_rights_to_position(
        state, rights, eligible_quantity=100, application_date=EX,
        election=RightsElection.PARTICIPATE,
        fractional_policy=FractionalSharePolicy.REJECT
    )
    state = apply_bonus_to_position(
        state, bonus, eligible_quantity=100,
        pre_action_reference_price=Decimal("10"), application_date=EX,
        fractional_policy=FractionalSharePolicy.REJECT
    )
    state = settle_dividend_receivable(state, entitlement, application_date=EX)
    theoretical_ex = (
        Decimal("10") - Decimal("0.3") + Decimal("0.2") * Decimal("8")
    ) / (Decimal(1) + Decimal("0.3") + Decimal("0.2"))

    assert state.quantity == 150
    assert state.cash == Decimal("870")
    assert state.dividend_receivable == 0
    assert state.total_cost == Decimal("1160")
    assert state.nav(theoretical_ex) == pre_nav
    assert [entry.action_type for entry in state.audit] == [
        "cash_dividend_entitlement",
        "rights_settlement",
        "bonus_transfer_credit",
        "cash_dividend_payment",
    ]
    assert sum((entry.pnl_delta for entry in state.audit), Decimal(0)) == Decimal("30")


def test_duplicate_stage_application_is_rejected() -> None:
    dividend = events()[0]
    entitlement = calculate_cash_entitlement(
        dividend, eligible_quantity=100, as_of=RECORD,
        tax_policy=FlatDividendTaxPolicy("zero-tax-v1", Decimal(0))
    )
    state = recognize_dividend_entitlement(
        PositionState(SECURITY, 100, Decimal("1000"), Decimal("1000")),
        entitlement, application_date=EX
    )

    with pytest.raises(DuplicateActionApplicationError):
        recognize_dividend_entitlement(state, entitlement, application_date=EX)


def test_share_events_cannot_be_applied_before_credit_or_settlement() -> None:
    _, bonus, rights = events()
    later_bonus = BonusShareEvent(
        bonus.security_id, bonus.announcement_date, bonus.record_date, bonus.ex_date,
        date(2024, 5, 10), bonus.bonus_ratio, bonus.transfer_ratio,
        bonus.source_identity, bonus.version
    )
    state = PositionState(SECURITY, 100, Decimal("1000"), Decimal("1000"))
    with pytest.raises(ValueError, match="share_credit_date"):
        apply_bonus_to_position(
            state, later_bonus, eligible_quantity=100,
            pre_action_reference_price=Decimal("10"), application_date=EX,
            fractional_policy=FractionalSharePolicy.REJECT
        )
    later_rights = RightsIssue(
        rights.security_id, rights.announcement_date, rights.record_date, rights.ex_date,
        date(2024, 5, 10), rights.rights_ratio, rights.subscription_price,
        rights.source_identity, rights.version
    )
    with pytest.raises(ValueError, match="settlement_date"):
        apply_rights_to_position(
            state, later_rights, eligible_quantity=100, application_date=EX,
            election=RightsElection.PARTICIPATE,
            fractional_policy=FractionalSharePolicy.REJECT
        )
