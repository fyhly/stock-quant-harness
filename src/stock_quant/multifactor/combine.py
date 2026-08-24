"""Aligned, signed and fully traceable linear factor combination."""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from enum import Enum
from typing import Iterable, Optional, Tuple

from stock_quant.domain import SecurityId


class FactorCombinationError(ValueError):
    pass


class FactorMissingPolicy(str, Enum):
    REJECT = "REJECT"
    ZERO = "ZERO"


@dataclass(frozen=True, order=True)
class FactorSpec:
    name: str
    signed_weight: Decimal
    lineage_identity: str


@dataclass(frozen=True)
class FactorInput:
    as_of: date
    security_id: SecurityId
    values: Tuple[Tuple[str, Optional[Decimal]], ...]


@dataclass(frozen=True)
class CompositeScore:
    as_of: date
    security_id: SecurityId
    score: Decimal
    contributions: Tuple[Tuple[str, Decimal], ...]
    lineage: Tuple[Tuple[str, str], ...]
    missing_policy: FactorMissingPolicy


def combine_factors(
    rows: Iterable[FactorInput],
    specs: Iterable[FactorSpec],
    *,
    missing_policy: FactorMissingPolicy,
) -> Tuple[CompositeScore, ...]:
    factors = tuple(sorted(specs))
    names = tuple(item.name for item in factors)
    if (
        not factors
        or names != tuple(sorted(set(names)))
        or any(
            not item.name
            or not item.signed_weight.is_finite()
            or len(item.lineage_identity) != 64
            for item in factors
        )
    ):
        raise FactorCombinationError("factor specifications are invalid")
    ordered = tuple(sorted(rows, key=lambda item: (item.as_of, item.security_id)))
    keys = tuple((item.as_of, item.security_id) for item in ordered)
    if keys != tuple(sorted(set(keys))):
        raise FactorCombinationError("factor matrix keys must be unique")
    output = []
    for row in ordered:
        if tuple(name for name, _ in row.values) != names:
            raise FactorCombinationError("factor row is not aligned to specifications")
        contributions = []
        for spec, (_, value) in zip(factors, row.values):
            if value is None:
                if missing_policy is FactorMissingPolicy.REJECT:
                    raise FactorCombinationError("missing factor rejected by policy")
                value = Decimal(0)
            if not value.is_finite():
                raise FactorCombinationError("factor value must be finite")
            contributions.append((spec.name, spec.signed_weight * value))
        output.append(
            CompositeScore(
                row.as_of,
                row.security_id,
                sum((value for _, value in contributions), Decimal(0)),
                tuple(contributions),
                tuple((item.name, item.lineage_identity) for item in factors),
                missing_policy,
            )
        )
    return tuple(output)
