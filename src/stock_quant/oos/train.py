"""Capability-limited deterministic training."""

from dataclasses import dataclass
from datetime import date
import hashlib
from typing import Callable, Generic, Mapping, Optional, Tuple, TypeVar

from stock_quant.oos.windows import OOSWindowSet


T = TypeVar("T")


class BoundedAccessError(ValueError):
    pass


class TrainContext(Generic[T]):
    def __init__(self, windows: OOSWindowSet, data: Mapping[date, T]) -> None:
        self._window = windows.train
        self._data = {
            day: value for day, value in data.items() if windows.train.contains(day)
        }

    def get(self, day: date) -> T:
        if not self._window.contains(day):
            raise BoundedAccessError("date is outside the train window")
        try:
            return self._data[day]
        except KeyError as exc:
            raise BoundedAccessError("train data is missing for date") from exc


@dataclass(frozen=True)
class FittedArtifact:
    artifact: bytes
    frozen_config: bytes
    artifact_identity: str
    config_identity: str


@dataclass(frozen=True)
class TrainRecord:
    window_identity: str
    succeeded: bool
    fitted: Optional[FittedArtifact]
    failure_type: str
    failure_message: str


def run_train(
    windows: OOSWindowSet,
    data: Mapping[date, T],
    fit: Callable[[TrainContext[T]], Tuple[bytes, bytes]],
) -> TrainRecord:
    context = TrainContext(windows, data)
    try:
        artifact, config = fit(context)
        fitted = FittedArtifact(
            artifact,
            config,
            hashlib.sha256(artifact).hexdigest(),
            hashlib.sha256(config).hexdigest(),
        )
        return TrainRecord(windows.identity, True, fitted, "", "")
    except Exception as exc:
        return TrainRecord(windows.identity, False, None, type(exc).__name__, str(exc))
