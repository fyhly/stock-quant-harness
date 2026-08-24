"""Fixed non-bypassable risk pipeline and explicit risk budgets."""

from dataclasses import dataclass
from decimal import Decimal
from typing import Tuple

from stock_quant.backtest.rebalance import (
    create_rebalance_intent,
    RebalanceIntent,
    TargetWeight,
)
from stock_quant.domain import SecurityId
from stock_quant.portfolio import PortfolioWeight, PortfolioWeights
from stock_quant.risk.api import (
    RiskAdjustment,
    RiskContractError,
    RiskDecision,
    RiskRequest,
)
from stock_quant.risk.exposure import apply_cash_exposure_limits
from stock_quant.risk.sector import apply_sector_limit
from stock_quant.risk.single_name import apply_single_name_limit
from stock_quant.risk.turnover import apply_turnover_limit


@dataclass(frozen=True, order=True)
class NameRiskBudget:
    security_id: SecurityId
    maximum_weight: Decimal


@dataclass(frozen=True, order=True)
class SectorRiskBudget:
    industry_code: str
    maximum_exposure: Decimal


@dataclass(frozen=True)
class RiskBudgets:
    names: Tuple[NameRiskBudget, ...]
    sectors: Tuple[SectorRiskBudget, ...]

    def __post_init__(self) -> None:
        name_ids = tuple(row.security_id for row in self.names)
        sector_ids = tuple(row.industry_code for row in self.sectors)
        if name_ids != tuple(sorted(set(name_ids))) or sector_ids != tuple(
            sorted(set(sector_ids))
        ):
            raise RiskContractError("risk budgets must be sorted and unique")
        values = tuple(row.maximum_weight for row in self.names) + tuple(
            row.maximum_exposure for row in self.sectors
        )
        if any(
            not value.is_finite() or not Decimal(0) <= value <= Decimal(1)
            for value in values
        ):
            raise RiskContractError("risk budgets must be in [0, 1]")
        if (
            sum((row.maximum_weight for row in self.names), Decimal(0)) > 1
            or sum((row.maximum_exposure for row in self.sectors), Decimal(0)) > 1
        ):
            raise RiskContractError("risk budget sums cannot exceed one")


@dataclass(frozen=True)
class RiskConfig:
    single_name_cap: Decimal
    sector_cap: Decimal
    turnover_cap: Decimal
    cash_floor: Decimal
    gross_cap: Decimal
    quantum: Decimal


def run_risk_engine(
    request: RiskRequest, config: RiskConfig, budgets: RiskBudgets
) -> RiskDecision:
    portfolio, budget_adjustments = _apply_budgets(request, budgets)
    portfolio, single = apply_single_name_limit(portfolio, config.single_name_cap)
    portfolio, sector = apply_sector_limit(
        portfolio,
        request.classifications,
        as_of=request.as_of,
        cap=config.sector_cap,
        quantum=config.quantum,
    )
    turnover = apply_turnover_limit(portfolio, request.current, config.turnover_cap)
    portfolio, exposure = apply_cash_exposure_limits(
        turnover.portfolio, cash_floor=config.cash_floor, gross_cap=config.gross_cap
    )
    adjustments = budget_adjustments + single + sector + turnover.adjustments + exposure
    return RiskDecision(request, portfolio, adjustments, ())


def approved_rebalance_intent(
    intent_id: str, decision: RiskDecision
) -> RebalanceIntent:
    return create_rebalance_intent(
        intent_id,
        decision.request.as_of,
        (TargetWeight(row.security_id, row.weight) for row in decision.output.weights),
    )


def _apply_budgets(
    request: RiskRequest, budgets: RiskBudgets
) -> Tuple[PortfolioWeights, Tuple[RiskAdjustment, ...]]:
    name_caps = {row.security_id: row.maximum_weight for row in budgets.names}
    sector_caps = {row.industry_code: row.maximum_exposure for row in budgets.sectors}
    industries = {row.security_id: row.industry_code for row in request.classifications}
    provisional = tuple(
        PortfolioWeight(
            row.security_id, min(row.weight, name_caps.get(row.security_id, Decimal(1)))
        )
        for row in request.proposed.weights
    )
    totals = {
        code: sum(
            (row.weight for row in provisional if industries[row.security_id] == code),
            Decimal(0),
        )
        for code in set(industries.values())
    }
    output, adjustments = [], []
    original = {row.security_id: row.weight for row in request.proposed.weights}
    for row in provisional:
        cap = sector_caps.get(industries[row.security_id], Decimal(1))
        total = totals[industries[row.security_id]]
        after = row.weight if total <= cap or total == 0 else row.weight * cap / total
        output.append(PortfolioWeight(row.security_id, after))
        if after != original[row.security_id]:
            adjustments.append(
                RiskAdjustment(
                    "BUDGET",
                    row.security_id,
                    str(original[row.security_id]),
                    str(after),
                    "RISK_BUDGET",
                )
            )
    gross = sum((row.weight for row in output), Decimal(0))
    return PortfolioWeights(tuple(output), Decimal(1) - gross, Decimal(0)), tuple(
        adjustments
    )
