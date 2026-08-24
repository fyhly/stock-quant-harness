from datetime import date
from decimal import Decimal

import pytest

from stock_quant.actions import (
    apply_cash_dividend,
    calculate_cash_entitlement,
    CashDividend,
    FlatDividendTaxPolicy,
)
from stock_quant.domain import Exchange, SecurityId


EVENT = CashDividend(
    SecurityId("600000", Exchange.SHANGHAI),
    date(2024, 1, 1),
    date(2024, 5, 8),
    date(2024, 5, 9),
    date(2024, 5, 15),
    Decimal("0.30"),
    "a" * 64,
    "v1",
)
POLICY = FlatDividendTaxPolicy("flat-20-v1", Decimal("0.20"))


def test_exact_entitlement_and_payable_application_have_no_false_pnl() -> None:
    entitlement = calculate_cash_entitlement(
        EVENT, eligible_quantity=101, as_of=EVENT.record_date, tax_policy=POLICY
    )
    application = apply_cash_dividend(
        entitlement, application_date=EVENT.pay_date
    )

    assert entitlement.gross_cash == Decimal("30.30")
    assert entitlement.tax_cash == Decimal("6.0600")
    assert entitlement.net_cash == Decimal("24.2400")
    assert application.cash_delta == Decimal("24.2400")
    assert application.dividend_receivable_delta == Decimal("-24.2400")
    assert application.pnl_delta == Decimal(0)


def test_ex_date_does_not_credit_cash_before_pay_date() -> None:
    entitlement = calculate_cash_entitlement(
        EVENT, eligible_quantity=100, as_of=EVENT.ex_date, tax_policy=POLICY
    )

    with pytest.raises(ValueError, match="pay_date"):
        apply_cash_dividend(entitlement, application_date=EVENT.ex_date)
    assert apply_cash_dividend(
        entitlement, application_date=EVENT.pay_date
    ).cash_delta == Decimal("24.0000")


def test_before_record_date_and_invalid_quantity_are_rejected() -> None:
    with pytest.raises(ValueError, match="record_date"):
        calculate_cash_entitlement(
            EVENT,
            eligible_quantity=100,
            as_of=date(2024, 5, 7),
            tax_policy=POLICY,
        )
    with pytest.raises(ValueError, match="nonnegative"):
        calculate_cash_entitlement(
            EVENT, eligible_quantity=-1, as_of=EVENT.record_date, tax_policy=POLICY
        )


def test_zero_quantity_is_exact_zero() -> None:
    entitlement = calculate_cash_entitlement(
        EVENT, eligible_quantity=0, as_of=EVENT.record_date, tax_policy=POLICY
    )

    assert entitlement.gross_cash == entitlement.tax_cash == entitlement.net_cash == 0


def test_invalid_tax_policy_is_rejected() -> None:
    with pytest.raises(ValueError, match="rate"):
        FlatDividendTaxPolicy("bad", Decimal("1.01"))
