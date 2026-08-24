"""Predeclared finite validation evaluation and deterministic freezing."""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
import hashlib
from typing import Callable, Generic, Mapping, Optional, Tuple, TypeVar

from stock_quant.oos.train import BoundedAccessError, FittedArtifact
from stock_quant.oos.windows import OOSWindowSet


T = TypeVar("T")


@dataclass(frozen=True, order=True)
class ParameterCandidate:
    candidate_id: str
    config: bytes

    def __post_init__(self) -> None:
        if not self.candidate_id or not self.config:
            raise ValueError("candidate id and config are required")


class ValidationContext(Generic[T]):
    def __init__(
        self, windows: OOSWindowSet, data: Mapping[date, T], fitted: FittedArtifact
    ) -> None:
        self._window = windows.validation
        self._data = {
            day: value for day, value in data.items() if self._window.contains(day)
        }
        self.fitted_artifact = fitted.artifact
        self.fitted_identity = fitted.artifact_identity

    def get(self, day: date) -> T:
        if not self._window.contains(day):
            raise BoundedAccessError("date is outside the validation window")
        try:
            return self._data[day]
        except KeyError as exc:
            raise BoundedAccessError("validation data is missing for date") from exc


@dataclass(frozen=True)
class CandidateEvaluation:
    candidate_id: str
    config_identity: str
    succeeded: bool
    score: Optional[Decimal]
    failure_type: str
    failure_message: str


class ValidationFailedError(RuntimeError):
    """All predefined candidates failed, with the full audit trail retained."""

    def __init__(
        self,
        parameter_space_identity: str,
        evaluations: Tuple[CandidateEvaluation, ...],
    ) -> None:
        super().__init__("all predefined candidates failed validation")
        self.parameter_space_identity = parameter_space_identity
        self.evaluations = evaluations


@dataclass(frozen=True)
class FrozenSelection:
    window_identity: str
    parameter_space_identity: str
    selected_candidate_id: str
    selected_config: bytes
    selected_config_identity: str
    evaluations: Tuple[CandidateEvaluation, ...]


def run_validation(
    windows: OOSWindowSet,
    data: Mapping[date, T],
    fitted: FittedArtifact,
    candidates: Tuple[ParameterCandidate, ...],
    evaluate: Callable[[ValidationContext[T], ParameterCandidate], Decimal],
) -> FrozenSelection:
    ordered = tuple(sorted(candidates))
    if not ordered or len({item.candidate_id for item in ordered}) != len(ordered):
        raise ValueError("parameter space must be finite, nonempty, and unique")
    space_raw = b"|".join(
        item.candidate_id.encode() + b":" + item.config for item in ordered
    )
    space_identity = hashlib.sha256(space_raw).hexdigest()
    context = ValidationContext(windows, data, fitted)
    records = []
    for candidate in ordered:
        identity = hashlib.sha256(candidate.config).hexdigest()
        try:
            score = evaluate(context, candidate)
            if not score.is_finite():
                raise ValueError("validation score must be finite")
            records.append(
                CandidateEvaluation(
                    candidate.candidate_id, identity, True, score, "", ""
                )
            )
        except Exception as exc:
            records.append(
                CandidateEvaluation(
                    candidate.candidate_id,
                    identity,
                    False,
                    None,
                    type(exc).__name__,
                    str(exc),
                )
            )
    successful = [record for record in records if record.succeeded]
    if not successful:
        raise ValidationFailedError(space_identity, tuple(records))
    best = min(successful, key=lambda item: (-item.score, item.candidate_id))  # type: ignore[operator]
    selected = next(item for item in ordered if item.candidate_id == best.candidate_id)
    return FrozenSelection(
        windows.identity,
        space_identity,
        selected.candidate_id,
        selected.config,
        hashlib.sha256(selected.config).hexdigest(),
        tuple(records),
    )
