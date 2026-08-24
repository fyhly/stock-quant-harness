"""Immutable half-open train, validation and OOS windows."""

from dataclasses import dataclass
from datetime import date, timedelta
import hashlib
import json


class WindowValidationError(ValueError):
    pass


@dataclass(frozen=True, order=True)
class TimeWindow:
    start: date
    end: date

    def __post_init__(self) -> None:
        if (
            type(self.start) is not date
            or type(self.end) is not date
            or self.start >= self.end
        ):
            raise WindowValidationError(
                "window must be a nonempty half-open date interval"
            )

    def contains(self, day: date) -> bool:
        return self.start <= day < self.end


@dataclass(frozen=True)
class OOSWindowSet:
    train: TimeWindow
    validation: TimeWindow
    oos: TimeWindow
    embargo_days: int
    identity: str

    @classmethod
    def create(
        cls,
        train: TimeWindow,
        validation: TimeWindow,
        oos: TimeWindow,
        *,
        embargo_days: int = 0,
    ) -> "OOSWindowSet":
        if embargo_days < 0:
            raise WindowValidationError("embargo cannot be negative")
        gap = timedelta(days=embargo_days)
        if train.end + gap > validation.start or validation.end + gap > oos.start:
            raise WindowValidationError("windows overlap or violate the embargo")
        payload = {
            "train": [train.start.isoformat(), train.end.isoformat()],
            "validation": [validation.start.isoformat(), validation.end.isoformat()],
            "oos": [oos.start.isoformat(), oos.end.isoformat()],
            "embargo_days": embargo_days,
        }
        identity = hashlib.sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        return cls(train, validation, oos, embargo_days, identity)
