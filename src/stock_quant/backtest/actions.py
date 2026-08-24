"""Timeline-gated integration of Phase 4 pure corporate-action transitions."""

from dataclasses import dataclass, replace
from decimal import Decimal
from typing import Optional, Tuple

from stock_quant.actions import (
    apply_bonus_to_position,
    apply_rights_to_position,
    BonusShareEvent,
    calculate_cash_entitlement,
    CashDividend,
    CashDividendEntitlement,
    DuplicateActionApplicationError,
    FlatDividendTaxPolicy,
    FractionalSharePolicy,
    PositionState,
    recognize_dividend_entitlement,
    RightsElection,
    settle_dividend_receivable,
)
from stock_quant.actions.model import CorporateActionType
from stock_quant.backtest.timeline import EventKind, EventPhase, TimelineEvent


@dataclass(frozen=True)
class EligibleQuantitySnapshot:
    event_id: str
    quantity: int


@dataclass(frozen=True)
class ActionIntegrationState:
    position: PositionState
    eligibility: Tuple[EligibleQuantitySnapshot, ...] = ()
    cash_entitlements: Tuple[CashDividendEntitlement, ...] = ()


def capture_record_entitlement(
    state: ActionIntegrationState,
    action: CorporateActionType,
    event: TimelineEvent,
    *,
    tax_policy: Optional[FlatDividendTaxPolicy] = None,
) -> ActionIntegrationState:
    if event.kind is not EventKind.ENTITLEMENT or event.phase is not EventPhase.RECORD_ENTITLEMENT:
        raise ValueError("record snapshot requires RECORD_ENTITLEMENT event")
    if event.trading_day.value != action.record_date:
        raise ValueError("record snapshot event date must equal action record_date")
    if any(item.event_id == action.event_id for item in state.eligibility):
        raise ValueError("corporate-action eligibility already captured")
    snapshot = EligibleQuantitySnapshot(action.event_id, state.position.quantity)
    entitlements = state.cash_entitlements
    if isinstance(action, CashDividend):
        if tax_policy is None:
            raise ValueError("cash dividend requires explicit tax_policy")
        entitlement = calculate_cash_entitlement(
            action,
            eligible_quantity=snapshot.quantity,
            as_of=action.record_date,
            tax_policy=tax_policy,
        )
        entitlements += (entitlement,)
    return replace(
        state,
        eligibility=state.eligibility + (snapshot,),
        cash_entitlements=entitlements,
    )


def apply_pre_market_action(
    state: ActionIntegrationState,
    action: CorporateActionType,
    event: TimelineEvent,
    *,
    fractional_policy: Optional[FractionalSharePolicy] = None,
    rights_election: Optional[RightsElection] = None,
    pre_action_reference_price: Optional[Decimal] = None,
) -> ActionIntegrationState:
    if (
        event.kind is not EventKind.CORPORATE_ACTION
        or event.phase is not EventPhase.PRE_MARKET_ACTIONS
    ):
        raise ValueError("action application requires PRE_MARKET_ACTIONS event")
    quantity = _eligible_quantity(state, action.event_id)
    position = state.position
    on_date = event.trading_day.value
    if isinstance(action, CashDividend):
        entitlement = _cash_entitlement(state, action.event_id)
        if on_date == action.ex_date and (
            f"{action.event_id}:ENTITLEMENT" not in position.applied_ledger
        ):
            position = recognize_dividend_entitlement(
                position, entitlement, application_date=on_date
            )
        elif on_date == action.pay_date:
            position = settle_dividend_receivable(
                position, entitlement, application_date=on_date
            )
        elif on_date == action.ex_date:
            raise DuplicateActionApplicationError(
                "dividend entitlement stage already applied"
            )
        else:
            raise ValueError("cash action date is neither pending ex nor pay stage")
    elif isinstance(action, BonusShareEvent):
        if fractional_policy is None or pre_action_reference_price is None:
            raise ValueError("bonus application requires explicit policies/reference")
        if on_date != action.share_credit_date:
            raise ValueError("bonus event must run on share_credit_date")
        position = apply_bonus_to_position(
            position,
            action,
            eligible_quantity=quantity,
            pre_action_reference_price=pre_action_reference_price,
            application_date=on_date,
            fractional_policy=fractional_policy,
        )
    else:
        if fractional_policy is None or rights_election is None:
            raise ValueError("rights application requires explicit policies")
        if on_date != action.settlement_date:
            raise ValueError("rights event must run on settlement_date")
        position = apply_rights_to_position(
            position,
            action,
            eligible_quantity=quantity,
            application_date=on_date,
            election=rights_election,
            fractional_policy=fractional_policy,
        )
    return replace(state, position=position)


def _eligible_quantity(state: ActionIntegrationState, event_id: str) -> int:
    for item in state.eligibility:
        if item.event_id == event_id:
            return item.quantity
    raise ValueError("record-date eligible quantity was not captured")


def _cash_entitlement(
    state: ActionIntegrationState, event_id: str
) -> CashDividendEntitlement:
    for item in state.cash_entitlements:
        if item.event_id == event_id:
            return item
    raise ValueError("cash entitlement was not captured")
