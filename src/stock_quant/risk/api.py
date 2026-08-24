"""Typed deterministic point-in-time risk contracts."""

from dataclasses import dataclass
import re
from typing import Iterable, Tuple

from stock_quant.domain import SecurityId, TradingDay
from stock_quant.portfolio import PortfolioWeights


_IDENTITY = re.compile(r"^[0-9a-f]{64}$")


class RiskContractError(ValueError):
    pass


class RiskInfeasibleError(RiskContractError):
    def __init__(self, reasons: Tuple[str, ...]) -> None:
        self.reasons = reasons
        super().__init__("risk constraints infeasible: " + "; ".join(reasons))


@dataclass(frozen=True, order=True)
class PITClassification:
    security_id: SecurityId
    as_of: TradingDay
    industry_code: str
    taxonomy_identity: str


@dataclass(frozen=True)
class RiskRequest:
    as_of: TradingDay
    proposed: PortfolioWeights
    current: PortfolioWeights
    classifications: Tuple[PITClassification, ...]
    config_identity: str
    upstream_identity: str


@dataclass(frozen=True)
class RiskAdjustment:
    stage: str
    security_id: SecurityId
    before: str
    after: str
    reason: str


@dataclass(frozen=True)
class RiskDecision:
    request: RiskRequest
    output: PortfolioWeights
    adjustments: Tuple[RiskAdjustment, ...]
    rejections: Tuple[str, ...]


def create_risk_request(
    as_of: TradingDay,
    proposed: PortfolioWeights,
    current: PortfolioWeights,
    classifications: Iterable[PITClassification],
    *,
    config_identity: str,
    upstream_identity: str,
) -> RiskRequest:
    rows = tuple(sorted(classifications))
    ids = tuple(row.security_id for row in rows)
    required_ids = {row.security_id for row in proposed.weights} | {
        row.security_id for row in current.weights
    }
    if ids != tuple(sorted(set(ids))) or set(ids) != required_ids:
        raise RiskContractError(
            "classifications must align uniquely to portfolio names"
        )
    if any(row.as_of != as_of for row in rows):
        raise RiskContractError("classification as-of mismatch")
    if any(
        not row.industry_code.strip() or not _IDENTITY.fullmatch(row.taxonomy_identity)
        for row in rows
    ):
        raise RiskContractError("invalid classification identity")
    if not _IDENTITY.fullmatch(config_identity) or not _IDENTITY.fullmatch(
        upstream_identity
    ):
        raise RiskContractError("invalid risk identity")
    _validate_portfolio(proposed)
    _validate_portfolio(current)
    return RiskRequest(
        as_of, proposed, current, rows, config_identity, upstream_identity
    )


def _validate_portfolio(portfolio: PortfolioWeights) -> None:
    ids = tuple(row.security_id for row in portfolio.weights)
    total = sum((row.weight for row in portfolio.weights), portfolio.cash_weight)
    if (
        ids != tuple(sorted(set(ids)))
        or total != 1
        or any(row.weight < 0 for row in portfolio.weights)
    ):
        raise RiskContractError(
            "portfolio must be sorted, unique, nonnegative and normalized"
        )
