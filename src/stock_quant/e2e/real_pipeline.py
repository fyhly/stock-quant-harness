"""Offline-only pipeline over the committed real A-share fixture."""

from dataclasses import dataclass
from datetime import date, datetime, time
from decimal import Decimal
from pathlib import Path
from typing import Dict, Tuple
from zoneinfo import ZoneInfo

import pyarrow.parquet as pq  # type: ignore[import-untyped]

from stock_quant.data import DailyBar, DailyBarSeries
from stock_quant.domain import (
    ListingLifecycle,
    SecurityId,
    StatusInterval,
    STStatus,
    STStatusHistory,
    TradeStatus,
    TradeStatusHistory,
    TradingCalendar,
    TradingDay,
    TradingSession,
)
from stock_quant.features import PriceObservation, trailing_return, trailing_volatility
from stock_quant.portfolio import equal_weight
from stock_quant.risk import (
    approved_rebalance_intent,
    create_risk_request,
    PITClassification,
    RiskBudgets,
    RiskConfig,
    RiskDecision,
    run_risk_engine,
)
from stock_quant.strategy import (
    BoundaryTiePolicy,
    create_score_intent,
    FeatureScore,
    RankMissingPolicy,
    rebalance_schedule,
    RebalanceFrequency,
    select_top_n,
)
from stock_quant.actions import RawExecutionBar, RawExecutionPriceView
from stock_quant.backtest import (
    AccountState,
    create_backtest_result,
    EquityPoint,
    execute_next_open,
    HoldingSnapshot,
    PriceLimitRule,
    PriceLimitSchedule,
    RawMark,
    RebalanceIntent,
    SlippageModel,
    SuspensionConstraint,
    TradingCostRule,
    TradingCostSchedule,
    value_account,
)
from stock_quant.backtest.rebalance import plan_rebalance
from stock_quant.backtest.result import BacktestResult
from stock_quant.domain import MarketSegment
from stock_quant.universe import (
    HistoricalLiquidityFilter,
    HistoricalSTFilter,
    HistoricalTradeStatusFilter,
    IndexId,
    IndexMembership,
    IndexMembershipHistory,
    LiquidityPolicy,
    ListingHistoryFilter,
    SecurityMaster,
    SecurityMetadata,
    STEligibilityPolicy,
    UniverseEngine,
    UniverseResult,
)


@dataclass(frozen=True)
class RealFeatureRow:
    security_id: SecurityId
    momentum_20: Decimal
    realized_volatility_20: Decimal


@dataclass(frozen=True)
class RealFeatureClosure:
    decision_day: TradingDay
    decision_cutoff: datetime
    rows: Tuple[RealFeatureRow, ...]
    lineage: str


@dataclass(frozen=True)
class RealAllocationClosure:
    risk_decision: RiskDecision
    rebalance_intent: RebalanceIntent


def load_real_bars(
    root: Path,
) -> Tuple[TradingCalendar, Dict[SecurityId, DailyBarSeries]]:
    rows = pq.read_table(root / "bars.parquet").to_pylist()
    grouped: Dict[SecurityId, list[DailyBar]] = {}
    days = set()
    for row in rows:
        security = SecurityId.parse(row["security_id"])
        day = TradingDay(date.fromisoformat(row["trading_day"]))
        days.add(day)
        grouped.setdefault(security, []).append(
            DailyBar(
                security,
                day,
                Decimal(row["open"]),
                Decimal(row["high"]),
                Decimal(row["low"]),
                Decimal(row["close"]),
                int(row["volume_lots"]) * 100,
                Decimal(row["amount_yuan"]),
            )
        )
    session = TradingSession("day", time(9, 30), time(15))
    calendar = TradingCalendar(
        {day: (session,) for day in days},
        coverage_start=min(day.value for day in days),
        coverage_end=max(day.value for day in days),
        timezone="Asia/Shanghai",
    )
    return calendar, {
        security: DailyBarSeries(
            security, sorted(bars, key=lambda bar: bar.trading_day)
        )
        for security, bars in grouped.items()
    }


def build_real_universe(root: Path, as_of: date) -> UniverseResult:
    calendar, bars = load_real_bars(root)
    securities = tuple(sorted(bars))
    master = SecurityMaster(
        SecurityMetadata(security, str(security)) for security in securities
    )
    listings = {
        security: ListingLifecycle(security, date(1991, 1, 1))
        for security in securities
    }
    st = {
        security: STStatusHistory([StatusInterval(STStatus.NORMAL, date(1991, 1, 1))])
        for security in securities
    }
    trade = {
        security: TradeStatusHistory(
            [StatusInterval(TradeStatus.TRADING, date(1991, 1, 1))]
        )
        for security in securities
    }
    index_id = IndexId("REAL_SAMPLE_V1")
    index = IndexMembershipHistory(
        index_id,
        [
            IndexMembership(index_id, security, date(2023, 1, 1), date(2025, 1, 1))
            for security in securities
        ],
        coverage_start=date(2023, 1, 1),
        coverage_end=date(2024, 12, 31),
    )
    historical_bars = {
        security: DailyBarSeries(
            security, (bar for bar in series.bars if bar.trading_day.value < as_of)
        )
        for security, series in bars.items()
    }
    engine = UniverseEngine(
        rule_version="real-universe-v1",
        master=master,
        listing_filter=ListingHistoryFilter(listings),
        st_filter=HistoricalSTFilter(st, STEligibilityPolicy("exclude-st-v1")),
        trade_filter=HistoricalTradeStatusFilter(trade),
        index_history=index,
        liquidity_filter=HistoricalLiquidityFilter(
            calendar, LiquidityPolicy("real-liquidity-v1", 20, Decimal(0), Decimal(0))
        ),
        bars=historical_bars,
    )
    return engine.build(as_of)


def compute_real_features(root: Path, decision_day: TradingDay) -> RealFeatureClosure:
    import json

    calendar, bars = load_real_bars(root)
    cutoff = datetime.combine(decision_day.value, time(15), ZoneInfo("Asia/Shanghai"))
    output = []
    for security, series in sorted(bars.items()):
        observations = tuple(
            PriceObservation(
                security,
                bar.trading_day,
                bar.close,
                datetime.combine(
                    bar.trading_day.value, time(16), ZoneInfo("Asia/Shanghai")
                ),
                "eastmoney-unadjusted-fqt0-v1",
            )
            for bar in series.bars
            if bar.trading_day < decision_day
        )
        momentum = trailing_return(
            observations,
            security_id=security,
            decision_day=decision_day,
            decision_cutoff=cutoff,
            calendar=calendar,
            sessions=20,
            view_identity="eastmoney-unadjusted-fqt0-v1",
        )
        volatility = trailing_volatility(
            observations,
            security_id=security,
            decision_day=decision_day,
            decision_cutoff=cutoff,
            calendar=calendar,
            sessions=20,
        )
        output.append(RealFeatureRow(security, momentum, volatility.realized))
    manifest = json.loads((root / "manifest.json").read_text())
    return RealFeatureClosure(
        decision_day, cutoff, tuple(output), manifest["normalized_sha256"]
    )


def build_real_allocation(
    root: Path, decision_day: TradingDay
) -> RealAllocationClosure:
    calendar, _ = load_real_bars(root)
    monthly = rebalance_schedule(
        calendar,
        start=calendar.trading_days[0],
        end=calendar.trading_days[-1],
        frequency=RebalanceFrequency.MONTHLY,
    )
    if decision_day not in {item.decision_day for item in monthly}:
        raise ValueError("decision day is not a monthly scheduled close")
    features = compute_real_features(root, decision_day)
    feature_scores = tuple(
        FeatureScore(
            row.security_id, row.momentum_20, features.decision_cutoff, features.lineage
        )
        for row in features.rows
    )
    score_intent = create_score_intent(
        decision_day,
        features.decision_cutoff,
        feature_scores,
        universe_identity=features.lineage,
        config_identity="1" * 64,
        data_identity=features.lineage,
    )
    selected = select_top_n(
        score_intent.scores,
        top_n=1,
        ascending=False,
        missing_policy=RankMissingPolicy.REJECT,
        boundary_ties=BoundaryTiePolicy.SECURITY_ID,
    )
    portfolio = equal_weight(
        selected.selected, cash_target=Decimal("0.2"), quantum=Decimal("0.0001")
    )
    classifications = tuple(
        PITClassification(row.security_id, decision_day, "BANK", "2" * 64)
        for row in portfolio.weights
    )
    request = create_risk_request(
        decision_day,
        portfolio,
        equal_weight((), cash_target=Decimal(1), quantum=Decimal("0.0001")),
        classifications,
        config_identity="3" * 64,
        upstream_identity=features.lineage,
    )
    decision = run_risk_engine(
        request,
        RiskConfig(
            Decimal("0.8"),
            Decimal("0.8"),
            Decimal(1),
            Decimal("0.2"),
            Decimal("0.8"),
            Decimal("0.0001"),
        ),
        RiskBudgets((), ()),
    )
    return RealAllocationClosure(
        decision, approved_rebalance_intent("real-monthly-v1", decision)
    )


def run_real_backtest(root: Path, decision_day: TradingDay) -> BacktestResult:
    calendar, bars = load_real_bars(root)
    allocation = build_real_allocation(root, decision_day)
    account = AccountState(Decimal("100000"))
    marks = {
        target.security_id: RawMark(
            target.security_id,
            decision_day,
            next(
                bar.close
                for bar in bars[target.security_id].bars
                if bar.trading_day == decision_day
            ),
        )
        for target in allocation.rebalance_intent.targets
    }
    plan = plan_rebalance(
        allocation.rebalance_intent, account=account, marks=marks, calendar=calendar
    )
    fills = []
    for order in plan.orders:
        series = bars[order.security_id]
        raw = next(bar for bar in series.bars if bar.trading_day == order.fill_day)
        prior_close = next(
            bar.close
            for bar in reversed(series.bars)
            if bar.trading_day < order.fill_day
        )
        execution_bar = RawExecutionBar(
            raw.security_id,
            raw.trading_day,
            raw.open,
            raw.high,
            raw.low,
            raw.close,
            raw.volume,
            raw.amount,
            "real-eastmoney-v1",
        )
        outcome = execute_next_open(
            order,
            view=RawExecutionPriceView(order.security_id, (execution_bar,)),
            account=account,
            calendar=calendar,
            suspension=SuspensionConstraint(
                {
                    order.security_id: TradeStatusHistory(
                        [StatusInterval(TradeStatus.TRADING, date(2023, 1, 1))]
                    )
                }
            ),
            price_limits=PriceLimitSchedule(
                "ashare-main-v1",
                [
                    PriceLimitRule(
                        MarketSegment.MAIN_BOARD,
                        date(2000, 1, 1),
                        None,
                        Decimal("0.1"),
                    )
                ],
            ),
            prior_close=prior_close,
            st_status=STStatus.NORMAL,
            costs=TradingCostSchedule(
                "real-cost-v1",
                [
                    TradingCostRule(
                        date(2023, 1, 1),
                        None,
                        Decimal("0.0003"),
                        Decimal(5),
                        Decimal(0),
                        Decimal(0),
                        Decimal("0.0005"),
                    )
                ],
            ),
            slippage=SlippageModel("zero-slippage-v1", Decimal(0)),
            participation_cap=Decimal("0.1"),
        )
        if outcome.fill is None:
            raise RuntimeError(f"real fixture order rejected: {outcome.rejection}")
        account = outcome.account
        fills.append(outcome.fill)
    fill_day = calendar.next_trading_day(decision_day.value)
    closing_marks = {
        security: RawMark(
            security,
            fill_day,
            next(bar.close for bar in series.bars if bar.trading_day == fill_day),
        )
        for security, series in bars.items()
        if account.position(security).quantity > 0
    }
    valuation = value_account(account, fill_day, closing_marks)
    return create_backtest_result(
        fills=fills,
        rejections=(),
        holdings=(HoldingSnapshot.from_account(fill_day, account),),
        equity=(EquityPoint(fill_day, valuation.equity),),
        trade_ledger=account.ledger,
        action_ledger_keys=(),
        config_identity="96f2b87a54dad4bfc1ca80600484757ba6de2cab3ad24e190f836f85037b95d4",
        data_identity=compute_real_features(root, decision_day).lineage,
        code_identity="13d4f979fc933cf1a3b5ca47cb25e7a43503963469d16df54e05cd568511879c",
    )
