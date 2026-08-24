"""Execution of a frozen configuration through an OOS-only capability."""

from dataclasses import dataclass
from datetime import date
import hashlib
from typing import Callable, Generic, Mapping, Optional, TypeVar

from stock_quant.oos.train import BoundedAccessError
from stock_quant.oos.validation import FrozenSelection
from stock_quant.oos.windows import OOSWindowSet


T = TypeVar("T")


class OOSContext(Generic[T]):
    def __init__(self, windows: OOSWindowSet, data: Mapping[date, T]) -> None:
        self._window = windows.oos
        self._data = {
            day: value for day, value in data.items() if windows.oos.contains(day)
        }

    def get(self, day: date) -> T:
        if not self._window.contains(day):
            raise BoundedAccessError("date is outside the OOS window")
        try:
            return self._data[day]
        except KeyError as exc:
            raise BoundedAccessError("OOS data is missing for date") from exc


@dataclass(frozen=True)
class OOSRecord:
    window_identity: str
    selected_candidate_id: str
    config_identity: str
    succeeded: bool
    result: bytes
    result_identity: Optional[str]
    failure_type: str
    failure_message: str


def run_oos(
    windows: OOSWindowSet,
    data: Mapping[date, T],
    selection: FrozenSelection,
    execute: Callable[[OOSContext[T], bytes], bytes],
) -> OOSRecord:
    if selection.window_identity != windows.identity:
        raise ValueError("selection window identity drift")
    if (
        hashlib.sha256(selection.selected_config).hexdigest()
        != selection.selected_config_identity
    ):
        raise ValueError("frozen selection config identity drift")
    context = OOSContext(windows, data)
    try:
        result = execute(context, selection.selected_config)
        return OOSRecord(
            windows.identity,
            selection.selected_candidate_id,
            selection.selected_config_identity,
            True,
            result,
            hashlib.sha256(result).hexdigest(),
            "",
            "",
        )
    except Exception as exc:
        return OOSRecord(
            windows.identity,
            selection.selected_candidate_id,
            selection.selected_config_identity,
            False,
            b"",
            None,
            type(exc).__name__,
            str(exc),
        )
