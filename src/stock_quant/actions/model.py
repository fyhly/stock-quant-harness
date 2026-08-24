"""Immutable corporate-action facts with distinct availability and effect dates."""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
import hashlib
import json
import re
from typing import Any, Dict, Protocol, Union

from stock_quant.domain import SecurityId


_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_SAFE_VERSION = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$")


class CorporateAction(Protocol):
    @property
    def security_id(self) -> SecurityId: ...

    @property
    def announcement_date(self) -> date: ...

    @property
    def record_date(self) -> date: ...

    @property
    def ex_date(self) -> date: ...

    @property
    def source_identity(self) -> str: ...

    @property
    def version(self) -> str: ...

    @property
    def event_id(self) -> str: ...


def _validate_common(action: CorporateAction) -> None:
    if not isinstance(action.security_id, SecurityId):
        raise TypeError("security_id must be a SecurityId")
    for name in ("announcement_date", "record_date", "ex_date"):
        if type(getattr(action, name)) is not date:
            raise TypeError(f"{name} must be a date, not a datetime")
    if not action.announcement_date <= action.record_date < action.ex_date:
        raise ValueError("dates must satisfy announcement <= record < ex")
    if not _SHA256.fullmatch(action.source_identity):
        raise ValueError("source_identity must be a lowercase SHA-256")
    if not _SAFE_VERSION.fullmatch(action.version):
        raise ValueError("invalid action version")


def _validate_decimal(name: str, value: Decimal, *, positive: bool) -> None:
    if not isinstance(value, Decimal):
        raise TypeError(f"{name} must be a Decimal")
    if not value.is_finite():
        raise ValueError(f"{name} must be finite")
    if positive and value <= 0:
        raise ValueError(f"{name} must be positive")
    if not positive and value < 0:
        raise ValueError(f"{name} cannot be negative")


def _identity(payload: Dict[str, Any]) -> str:
    encoded = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _common_payload(action: CorporateAction, action_type: str) -> Dict[str, Any]:
    return {
        "action_type": action_type,
        "announcement_date": action.announcement_date.isoformat(),
        "ex_date": action.ex_date.isoformat(),
        "record_date": action.record_date.isoformat(),
        "security_id": str(action.security_id),
        "source_identity": action.source_identity,
        "version": action.version,
    }


@dataclass(frozen=True)
class CashDividend:
    security_id: SecurityId
    announcement_date: date
    record_date: date
    ex_date: date
    pay_date: date
    cash_per_share: Decimal
    source_identity: str
    version: str

    def __post_init__(self) -> None:
        _validate_common(self)
        if type(self.pay_date) is not date or self.pay_date < self.ex_date:
            raise ValueError("pay_date must be a date on or after ex_date")
        _validate_decimal("cash_per_share", self.cash_per_share, positive=True)

    @property
    def event_id(self) -> str:
        payload = _common_payload(self, "cash_dividend")
        payload.update(
            {"cash_per_share": str(self.cash_per_share), "pay_date": self.pay_date.isoformat()}
        )
        return _identity(payload)


@dataclass(frozen=True)
class BonusShareEvent:
    security_id: SecurityId
    announcement_date: date
    record_date: date
    ex_date: date
    share_credit_date: date
    bonus_ratio: Decimal
    transfer_ratio: Decimal
    source_identity: str
    version: str

    def __post_init__(self) -> None:
        _validate_common(self)
        if (
            type(self.share_credit_date) is not date
            or self.share_credit_date < self.ex_date
        ):
            raise ValueError("share_credit_date must be on or after ex_date")
        _validate_decimal("bonus_ratio", self.bonus_ratio, positive=False)
        _validate_decimal("transfer_ratio", self.transfer_ratio, positive=False)
        if self.total_ratio <= 0:
            raise ValueError("bonus plus transfer ratio must be positive")

    @property
    def total_ratio(self) -> Decimal:
        return self.bonus_ratio + self.transfer_ratio

    @property
    def event_id(self) -> str:
        payload = _common_payload(self, "bonus_transfer")
        payload.update(
            {
                "bonus_ratio": str(self.bonus_ratio),
                "share_credit_date": self.share_credit_date.isoformat(),
                "transfer_ratio": str(self.transfer_ratio),
            }
        )
        return _identity(payload)


@dataclass(frozen=True)
class RightsIssue:
    security_id: SecurityId
    announcement_date: date
    record_date: date
    ex_date: date
    settlement_date: date
    rights_ratio: Decimal
    subscription_price: Decimal
    source_identity: str
    version: str

    def __post_init__(self) -> None:
        _validate_common(self)
        if type(self.settlement_date) is not date or self.settlement_date < self.ex_date:
            raise ValueError("settlement_date must be on or after ex_date")
        _validate_decimal("rights_ratio", self.rights_ratio, positive=True)
        _validate_decimal("subscription_price", self.subscription_price, positive=False)

    @property
    def event_id(self) -> str:
        payload = _common_payload(self, "rights_issue")
        payload.update(
            {
                "rights_ratio": str(self.rights_ratio),
                "settlement_date": self.settlement_date.isoformat(),
                "subscription_price": str(self.subscription_price),
            }
        )
        return _identity(payload)


CorporateActionType = Union[CashDividend, BonusShareEvent, RightsIssue]
