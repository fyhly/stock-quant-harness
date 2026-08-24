"""Pure audited position/cash transitions for corporate actions."""

from dataclasses import dataclass, replace
from datetime import date
from decimal import Decimal
from typing import Tuple

from stock_quant.actions.dividend import apply_cash_dividend, CashDividendEntitlement
from stock_quant.actions.model import BonusShareEvent, RightsIssue
from stock_quant.actions.rights import apply_rights_issue, RightsElection
from stock_quant.actions.shares import apply_bonus_shares, FractionalSharePolicy
from stock_quant.domain import SecurityId


class DuplicateActionApplicationError(ValueError):
    """Raised when a ledger stage has already been applied."""


@dataclass(frozen=True)
class PositionActionAudit:
    ledger_key: str
    event_id: str
    action_type: str
    application_date: date
    quantity_delta: int
    cash_delta: Decimal
    receivable_delta: Decimal
    total_cost_delta: Decimal
    pnl_delta: Decimal


@dataclass(frozen=True)
class PositionState:
    security_id: SecurityId
    quantity: int
    total_cost: Decimal
    cash: Decimal
    dividend_receivable: Decimal = Decimal(0)
    applied_ledger: Tuple[str, ...] = ()
    audit: Tuple[PositionActionAudit, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.security_id, SecurityId):
            raise TypeError("security_id must be a SecurityId")
        if type(self.quantity) is not int or self.quantity < 0:
            raise ValueError("quantity must be a nonnegative integer")
        for name in ("total_cost", "cash", "dividend_receivable"):
            value = getattr(self, name)
            if not isinstance(value, Decimal) or not value.is_finite():
                raise ValueError(f"{name} must be a finite Decimal")
        if self.total_cost < 0 or self.cash < 0 or self.dividend_receivable < 0:
            raise ValueError("position cost, cash, and receivable cannot be negative")
        if len(set(self.applied_ledger)) != len(self.applied_ledger):
            raise ValueError("applied ledger keys must be unique")

    def nav(self, market_price: Decimal) -> Decimal:
        if (
            not isinstance(market_price, Decimal)
            or not market_price.is_finite()
            or market_price < 0
        ):
            raise ValueError("market_price must be a nonnegative finite Decimal")
        return self.cash + self.dividend_receivable + Decimal(self.quantity) * market_price


def recognize_dividend_entitlement(
    state: PositionState,
    entitlement: CashDividendEntitlement,
    *,
    application_date: date,
) -> PositionState:
    _validate_identity(state, entitlement.security_id)
    if application_date < entitlement.ex_date:
        raise ValueError("dividend receivable cannot be recognized before ex_date")
    key = f"{entitlement.event_id}:ENTITLEMENT"
    _ensure_new(state, key)
    audit = PositionActionAudit(
        key, entitlement.event_id, "cash_dividend_entitlement", application_date,
        0, Decimal(0), entitlement.net_cash, Decimal(0), entitlement.net_cash
    )
    return _updated(
        state, ledger_key=key, audit=audit,
        dividend_receivable=state.dividend_receivable + entitlement.net_cash
    )


def settle_dividend_receivable(
    state: PositionState,
    entitlement: CashDividendEntitlement,
    *,
    application_date: date,
) -> PositionState:
    _validate_identity(state, entitlement.security_id)
    prerequisite = f"{entitlement.event_id}:ENTITLEMENT"
    if prerequisite not in state.applied_ledger:
        raise ValueError("dividend entitlement must be recognized before payment")
    key = f"{entitlement.event_id}:PAYMENT"
    _ensure_new(state, key)
    application = apply_cash_dividend(entitlement, application_date=application_date)
    if state.dividend_receivable < entitlement.net_cash:
        raise ValueError("dividend receivable balance is insufficient")
    audit = PositionActionAudit(
        key, entitlement.event_id, "cash_dividend_payment", application_date,
        0, application.cash_delta, application.dividend_receivable_delta,
        Decimal(0), application.pnl_delta
    )
    return _updated(
        state, ledger_key=key, audit=audit,
        cash=state.cash + application.cash_delta,
        dividend_receivable=state.dividend_receivable + application.dividend_receivable_delta
    )


def apply_bonus_to_position(
    state: PositionState,
    event: BonusShareEvent,
    *,
    eligible_quantity: int,
    pre_action_reference_price: Decimal,
    application_date: date,
    fractional_policy: FractionalSharePolicy,
) -> PositionState:
    _validate_identity(state, event.security_id)
    key = f"{event.event_id}:SHARE_CREDIT"
    _ensure_new(state, key)
    adjustment = apply_bonus_shares(
        event, quantity=eligible_quantity, total_cost=state.total_cost,
        pre_action_reference_price=pre_action_reference_price,
        application_date=application_date, fractional_policy=fractional_policy
    )
    audit = PositionActionAudit(
        key, event.event_id, "bonus_transfer_credit", application_date,
        adjustment.share_delta, Decimal(0), Decimal(0), Decimal(0), Decimal(0)
    )
    return _updated(
        state, ledger_key=key, audit=audit,
        quantity=state.quantity + adjustment.share_delta
    )


def apply_rights_to_position(
    state: PositionState,
    event: RightsIssue,
    *,
    eligible_quantity: int,
    application_date: date,
    election: RightsElection,
    fractional_policy: FractionalSharePolicy,
) -> PositionState:
    _validate_identity(state, event.security_id)
    key = f"{event.event_id}:RIGHTS_SETTLEMENT"
    _ensure_new(state, key)
    adjustment = apply_rights_issue(
        event, quantity=eligible_quantity, total_cost=state.total_cost,
        available_cash=state.cash, application_date=application_date,
        election=election, fractional_policy=fractional_policy
    )
    cost_delta = adjustment.new_total_cost - adjustment.old_total_cost
    audit = PositionActionAudit(
        key, event.event_id, "rights_settlement", application_date,
        adjustment.share_delta, adjustment.cash_delta, Decimal(0),
        cost_delta, Decimal(0)
    )
    return _updated(
        state, ledger_key=key, audit=audit,
        quantity=state.quantity + adjustment.share_delta,
        cash=state.cash + adjustment.cash_delta,
        total_cost=state.total_cost + cost_delta
    )


def _validate_identity(state: PositionState, security_id: SecurityId) -> None:
    if not isinstance(state, PositionState):
        raise TypeError("state must be a PositionState")
    if state.security_id != security_id:
        raise ValueError("position and corporate-action security identities differ")


def _ensure_new(state: PositionState, ledger_key: str) -> None:
    if ledger_key in state.applied_ledger:
        raise DuplicateActionApplicationError(f"already applied {ledger_key}")


def _updated(
    state: PositionState,
    *,
    ledger_key: str,
    audit: PositionActionAudit,
    **changes: object,
) -> PositionState:
    return replace(
        state,
        applied_ledger=state.applied_ledger + (ledger_key,),
        audit=state.audit + (audit,),
        **changes,  # type: ignore[arg-type]
    )
