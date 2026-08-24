"""Explicit rights-issue election and settlement calculation."""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal, ROUND_FLOOR
from enum import Enum

from stock_quant.actions.model import RightsIssue
from stock_quant.actions.shares import FractionalSharePolicy


class RightsElection(str, Enum):
    PARTICIPATE = "PARTICIPATE"
    DECLINE = "DECLINE"


@dataclass(frozen=True)
class RightsIssueAdjustment:
    event_id: str
    settlement_date: date
    election: RightsElection
    old_quantity: int
    exact_share_entitlement: Decimal
    share_delta: int
    discarded_fraction: Decimal
    new_quantity: int
    cash_delta: Decimal
    old_total_cost: Decimal
    new_total_cost: Decimal


def apply_rights_issue(
    event: RightsIssue,
    *,
    quantity: int,
    total_cost: Decimal,
    available_cash: Decimal,
    application_date: date,
    election: RightsElection,
    fractional_policy: FractionalSharePolicy,
) -> RightsIssueAdjustment:
    """Apply an explicit election no earlier than the settlement date."""

    if not isinstance(event, RightsIssue):
        raise TypeError("event must be RightsIssue")
    if type(quantity) is not int or quantity < 0:
        raise ValueError("quantity must be a nonnegative integer")
    for name, value in (("total_cost", total_cost), ("available_cash", available_cash)):
        if not isinstance(value, Decimal) or not value.is_finite() or value < 0:
            raise ValueError(f"{name} must be a nonnegative finite Decimal")
    if type(application_date) is not date:
        raise TypeError("application_date must be a date, not a datetime")
    if application_date < event.settlement_date:
        raise ValueError("rights shares cannot be used before settlement_date")
    if not isinstance(election, RightsElection):
        raise TypeError("election must be explicitly supplied")
    if not isinstance(fractional_policy, FractionalSharePolicy):
        raise TypeError("fractional_policy must be explicitly supplied")

    exact = Decimal(quantity) * event.rights_ratio
    integral = exact.to_integral_value(rounding=ROUND_FLOOR)
    fraction = exact - integral
    if fractional_policy is FractionalSharePolicy.REJECT and fraction != 0:
        raise ValueError("fractional entitlement rejected by explicit policy")
    if election is RightsElection.DECLINE:
        return RightsIssueAdjustment(
            event.event_id,
            application_date,
            election,
            quantity,
            exact,
            0,
            fraction,
            quantity,
            Decimal(0),
            total_cost,
            total_cost,
        )
    share_delta = int(integral)
    required_cash = Decimal(share_delta) * event.subscription_price
    if required_cash > available_cash:
        raise ValueError("insufficient cash for explicit rights participation")
    return RightsIssueAdjustment(
        event.event_id,
        application_date,
        election,
        quantity,
        exact,
        share_delta,
        fraction,
        quantity + share_delta,
        -required_cash,
        total_cost,
        total_cost + required_cash,
    )
