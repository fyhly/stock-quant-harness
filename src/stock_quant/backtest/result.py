"""Immutable complete backtest audit result and exact replay fingerprint."""

from dataclasses import dataclass
from decimal import Decimal
import hashlib
import json
import re
from typing import Any, Dict, Iterable, Tuple

from stock_quant.backtest.account import AccountState, TradeAccountingEntry
from stock_quant.backtest.constraints import RejectionCode
from stock_quant.backtest.execution import Fill
from stock_quant.domain import SecurityId, TradingDay


_SHA256 = re.compile(r"^[0-9a-f]{64}$")


class ReplayIdentityError(ValueError):
    pass


@dataclass(frozen=True)
class RejectionRecord:
    order_id: str
    trading_day: TradingDay
    code: RejectionCode


@dataclass(frozen=True)
class HoldingSnapshot:
    trading_day: TradingDay
    cash: Decimal
    positions: Tuple[Tuple[SecurityId, int, Decimal], ...]

    @classmethod
    def from_account(
        cls, trading_day: TradingDay, account: AccountState
    ) -> "HoldingSnapshot":
        return cls(
            trading_day,
            account.cash,
            tuple(
                (position.security_id, position.quantity, position.total_cost)
                for position in account.positions
            ),
        )


@dataclass(frozen=True)
class EquityPoint:
    trading_day: TradingDay
    equity: Decimal


@dataclass(frozen=True)
class BacktestResult:
    fills: Tuple[Fill, ...]
    rejections: Tuple[RejectionRecord, ...]
    holdings: Tuple[HoldingSnapshot, ...]
    equity: Tuple[EquityPoint, ...]
    trade_ledger: Tuple[TradeAccountingEntry, ...]
    action_ledger_keys: Tuple[str, ...]
    config_identity: str
    data_identity: str
    code_identity: str
    fingerprint: str


def create_backtest_result(
    *,
    fills: Iterable[Fill],
    rejections: Iterable[RejectionRecord],
    holdings: Iterable[HoldingSnapshot],
    equity: Iterable[EquityPoint],
    trade_ledger: Iterable[TradeAccountingEntry],
    action_ledger_keys: Iterable[str],
    config_identity: str,
    data_identity: str,
    code_identity: str,
) -> BacktestResult:
    result = BacktestResult(
        tuple(fills), tuple(rejections), tuple(holdings), tuple(equity),
        tuple(trade_ledger), tuple(action_ledger_keys), config_identity,
        data_identity, code_identity, ""
    )
    _validate_identities(result)
    fingerprint = hashlib.sha256(_canonical_bytes(result)).hexdigest()
    return BacktestResult(
        result.fills, result.rejections, result.holdings, result.equity,
        result.trade_ledger, result.action_ledger_keys, result.config_identity,
        result.data_identity, result.code_identity, fingerprint
    )


def verify_backtest_result(result: BacktestResult) -> None:
    _validate_identities(result)
    expected = hashlib.sha256(_canonical_bytes(result)).hexdigest()
    if result.fingerprint != expected:
        raise ReplayIdentityError("backtest replay fingerprint mismatch")


def _canonical_bytes(result: BacktestResult) -> bytes:
    payload: Dict[str, Any] = {
        "action_ledger_keys": list(result.action_ledger_keys),
        "code_identity": result.code_identity,
        "config_identity": result.config_identity,
        "data_identity": result.data_identity,
        "equity": [
            {"day": item.trading_day.value.isoformat(), "equity": str(item.equity)}
            for item in result.equity
        ],
        "fills": [
            {
                "costs": {
                    "commission": str(item.costs.commission),
                    "notional": str(item.costs.notional),
                    "rule_version": item.costs.rule_version,
                    "stamp_duty": str(item.costs.stamp_duty),
                    "total": str(item.costs.total),
                    "transfer_fee": str(item.costs.transfer_fee),
                },
                "day": item.trading_day.value.isoformat(),
                "order_id": item.order_id,
                "price": str(item.price),
                "quantity": item.quantity,
                "raw_open": str(item.raw_open),
                "security_id": str(item.security_id),
                "side": item.side.value,
                "slippage_version": item.slippage_version,
            }
            for item in result.fills
        ],
        "holdings": [
            {
                "cash": str(item.cash),
                "day": item.trading_day.value.isoformat(),
                "positions": [
                    [str(security_id), quantity, str(cost)]
                    for security_id, quantity, cost in item.positions
                ],
            }
            for item in result.holdings
        ],
        "rejections": [
            {"code": item.code.value, "day": item.trading_day.value.isoformat(),
             "order_id": item.order_id}
            for item in result.rejections
        ],
        "trade_ledger": [
            {
                "cash_delta": str(item.cash_delta),
                "cost_basis_delta": str(item.cost_basis_delta),
                "day": item.trading_day.value.isoformat(),
                "price": str(item.price),
                "quantity": item.quantity,
                "realized_pnl": str(item.realized_pnl),
                "security_id": str(item.security_id),
                "side": item.side,
            }
            for item in result.trade_ledger
        ],
    }
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _validate_identities(result: BacktestResult) -> None:
    for name in ("config_identity", "data_identity", "code_identity"):
        if not _SHA256.fullmatch(getattr(result, name)):
            raise ReplayIdentityError(f"{name} must be a lowercase SHA-256")
    if len(set(result.action_ledger_keys)) != len(result.action_ledger_keys):
        raise ReplayIdentityError("action ledger keys must be unique")
