"""Pure cash-dividend entitlement and payable-date application."""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from stock_quant.actions.model import CashDividend
from stock_quant.domain import SecurityId


@dataclass(frozen=True)
class FlatDividendTaxPolicy:
    version: str
    rate: Decimal

    def __post_init__(self) -> None:
        if not isinstance(self.version, str) or not self.version.strip():
            raise ValueError("tax policy version must be non-empty")
        if (
            not isinstance(self.rate, Decimal)
            or not self.rate.is_finite()
            or not Decimal(0) <= self.rate <= Decimal(1)
        ):
            raise ValueError("tax rate must be a finite Decimal in [0, 1]")

    def tax_due(self, gross_cash: Decimal) -> Decimal:
        return gross_cash * self.rate


@dataclass(frozen=True)
class CashDividendEntitlement:
    event_id: str
    security_id: SecurityId
    eligible_quantity: int
    record_date: date
    ex_date: date
    pay_date: date
    gross_cash: Decimal
    tax_cash: Decimal
    net_cash: Decimal
    tax_policy_version: str


@dataclass(frozen=True)
class CashDividendApplication:
    event_id: str
    application_date: date
    cash_delta: Decimal
    dividend_receivable_delta: Decimal
    pnl_delta: Decimal


def calculate_cash_entitlement(
    event: CashDividend,
    *,
    eligible_quantity: int,
    as_of: date,
    tax_policy: FlatDividendTaxPolicy,
) -> CashDividendEntitlement:
    """Calculate exact entitlement from record-date eligible shares."""

    if not isinstance(event, CashDividend):
        raise TypeError("event must be a CashDividend")
    if type(eligible_quantity) is not int or eligible_quantity < 0:
        raise ValueError("eligible_quantity must be a nonnegative integer")
    if type(as_of) is not date:
        raise TypeError("as_of must be a date, not a datetime")
    if as_of < event.record_date:
        raise ValueError("entitlement cannot be known before record_date")
    if not isinstance(tax_policy, FlatDividendTaxPolicy):
        raise TypeError("tax_policy must be FlatDividendTaxPolicy")
    gross = event.cash_per_share * Decimal(eligible_quantity)
    tax = tax_policy.tax_due(gross)
    return CashDividendEntitlement(
        event.event_id,
        event.security_id,
        eligible_quantity,
        event.record_date,
        event.ex_date,
        event.pay_date,
        gross,
        tax,
        gross - tax,
        tax_policy.version,
    )


def apply_cash_dividend(
    entitlement: CashDividendEntitlement, *, application_date: date
) -> CashDividendApplication:
    """Settle the receivable on/after pay date without recognizing new PnL."""

    if not isinstance(entitlement, CashDividendEntitlement):
        raise TypeError("entitlement must be CashDividendEntitlement")
    if type(application_date) is not date:
        raise TypeError("application_date must be a date, not a datetime")
    if application_date < entitlement.pay_date:
        raise ValueError("cash dividend cannot be credited before pay_date")
    return CashDividendApplication(
        entitlement.event_id,
        application_date,
        entitlement.net_cash,
        -entitlement.net_cash,
        Decimal(0),
    )
