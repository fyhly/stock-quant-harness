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
