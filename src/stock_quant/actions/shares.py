"""Pure bonus/transfer share quantity and cost-basis adjustment."""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal, ROUND_FLOOR
from enum import Enum

from stock_quant.actions.model import BonusShareEvent


class FractionalSharePolicy(str, Enum):
    ROUND_DOWN = "ROUND_DOWN"
    REJECT = "REJECT"


@dataclass(frozen=True)
class BonusShareAdjustment:
    event_id: str
    application_date: date
    old_quantity: int
    exact_share_entitlement: Decimal
    share_delta: int
    discarded_fraction: Decimal
    new_quantity: int
    old_total_cost: Decimal
    new_total_cost: Decimal
    new_average_cost: Decimal
    pre_action_reference_price: Decimal
    theoretical_post_action_price: Decimal
    pre_action_market_value: Decimal
    credited_market_value: Decimal
    discarded_fraction_value: Decimal


def apply_bonus_shares(
    event: BonusShareEvent,
    *,
    quantity: int,
    total_cost: Decimal,
    pre_action_reference_price: Decimal,
    application_date: date,
    fractional_policy: FractionalSharePolicy,
) -> BonusShareAdjustment:
    """Apply credited shares no earlier than the explicit share-credit date."""

    if not isinstance(event, BonusShareEvent):
        raise TypeError("event must be BonusShareEvent")
    if type(quantity) is not int or quantity < 0:
        raise ValueError("quantity must be a nonnegative integer")
    if (
        not isinstance(total_cost, Decimal)
        or not total_cost.is_finite()
        or total_cost < 0
    ):
        raise ValueError("total_cost must be a nonnegative finite Decimal")
    if (
        not isinstance(pre_action_reference_price, Decimal)
        or not pre_action_reference_price.is_finite()
        or pre_action_reference_price <= 0
    ):
        raise ValueError("pre_action_reference_price must be a positive Decimal")
    if type(application_date) is not date:
        raise TypeError("application_date must be a date, not a datetime")
    if application_date < event.share_credit_date:
        raise ValueError("bonus shares cannot be used before share_credit_date")
    if not isinstance(fractional_policy, FractionalSharePolicy):
        raise TypeError("fractional_policy must be explicitly supplied")

    exact_entitlement = Decimal(quantity) * event.total_ratio
    integral = exact_entitlement.to_integral_value(rounding=ROUND_FLOOR)
    fraction = exact_entitlement - integral
    if fractional_policy is FractionalSharePolicy.REJECT and fraction != 0:
        raise ValueError("fractional entitlement rejected by explicit policy")
    share_delta = int(integral)
    new_quantity = quantity + share_delta
    theoretical_post_price = pre_action_reference_price / (
        Decimal(1) + event.total_ratio
    )
    new_average_cost = (
        total_cost / Decimal(new_quantity) if new_quantity else Decimal(0)
    )
    credited_value = Decimal(new_quantity) * theoretical_post_price
    discarded_value = fraction * theoretical_post_price
    return BonusShareAdjustment(
        event.event_id,
        application_date,
        quantity,
        exact_entitlement,
        share_delta,
        fraction,
        new_quantity,
        total_cost,
        total_cost,
        new_average_cost,
        pre_action_reference_price,
        theoretical_post_price,
        Decimal(quantity) * pre_action_reference_price,
        credited_value,
        discarded_value,
    )
