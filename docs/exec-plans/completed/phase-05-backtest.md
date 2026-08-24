# Phase 5 ExecPlan — A-share Backtest Engine

Status: COMPLETED

## Objective

建立确定性、可重放、会计一致的离线股票回测核心，显式建模 A 股 T+1、停牌、涨跌停、费用、滑点、成交量和公司行动；策略仅提交调仓意图。

## Ordered task contracts

All tasks depend on the prior accepted milestone. Allowed scope: `stock_quant.backtest`, focused tests/exports/docs and explicitly named action/domain integration. Forbidden: Provider/network, adjusted research prices as fills, real account/broker/order submission, hidden same-bar future fills, strategy alpha/factor work, or weakening constraints for performance.

### P05-M5.1-T1 — Deterministic timeline
- Goal/output: typed events and stable event loop ordered by trading date, phase and deterministic sequence; explicit decision/order/fill timing.
- Tests/acceptance: order invariance, same-time tie policy, replay determinism, invalid/out-of-calendar events; no future execution.
- Risk: HIGH; Commit: `feat(backtest): add deterministic timeline`

### P05-M5.2-T1 — Cash, positions, valuation
- Goal/output: exact Decimal cash ledger, lots/positions and mark-to-raw-price valuation with accounting audit.
- Tests/acceptance: buy/sell deltas, cost basis, cash+market value=equity, missing/stale valuation fail policy.
- Risk: HIGH; Commit: `feat(backtest): add account and positions`

### P05-M5.3-T1 — T+1 sellability
- Goal/output: acquisition-date lots with frozen/sellable quantities released only on next supplied trading day.
- Tests/acceptance: same-day sell rejected, next-day release, partial lots, holidays, corporate-action quantities.
- Risk: HIGH; Commit: `feat(backtest): enforce t+1 sellability`

### P05-M5.4-T1 — Suspension
- Goal/output: execution constraint using historical TradeStatus while valuation remains separate.
- Tests/acceptance: suspended buy/sell rejected, unknown status fail closed, valuation still possible.
- Risk: HIGH; Commit: `feat(backtest): handle suspensions`

### P05-M5.5-T1 — Price limits
- Goal/output: versioned board/date-aware limit rules and conservative fillability checks using unadjusted prior close/current raw bar.
- Tests/acceptance: one-price up/down limit, buy/sell direction, board/rule boundaries, missing facts fail closed.
- Risk: HIGH; Commit: `feat(backtest): enforce price limits`

### P05-M5.6-T1 — Costs and taxes
- Goal/output: versioned exact commission/minimum/transfer/Stamp Duty rules separated by side/date.
- Tests/acceptance: buy/sell, minimum fee, rounding/date changes and zero/invalid cases.
- Risk: HIGH; Commit: `feat(backtest): add trading costs`

### P05-M5.7-T1 — Slippage and volume limits
- Goal/output: explicit deterministic slippage plus participation cap; fills use RawExecutionPriceView and cannot exceed liquidity/cash/quantity.
- Tests/acceptance: low volume, partial/rejected fills, direction, zero volume, cost interaction and deterministic results.
- Risk: HIGH; Commit: `feat(backtest): add slippage and volume limits`

### P05-M5.8-T1 — Corporate-action integration
- Goal/output: apply Phase 4 ledger transitions exactly once at declared stages before relevant valuation/execution phases.
- Tests/acceptance: dividends/bonus/rights over timeline, entitlement and credit separation, NAV continuity, duplicate replay rejection.
- Risk: HIGH; Commit: `feat(backtest): integrate corporate actions`

### P05-M5.9-T1 — Rebalance intent
- Goal/output: typed TargetWeight/rebalance intent converted deterministically into order intents using pre-trade equity, lots, cash and constraints; no fills inside strategy interface.
- Tests/acceptance: weights to buys/sells, cash/lot rounding, invalid weights, deterministic ordering and clear residual cash.
- Risk: HIGH; Commit: `feat(backtest): add rebalance interface`

### P05-M5.10-T1 — Result and replay
- Goal/output: immutable BacktestResult with trades/rejections/holdings/equity/ledger/config/data/code identities and exact replay fingerprint.
- Tests/acceptance: end-to-end constrained scenario, repeat exact match, tamper/identity failure and complete audit trail.
- Risk: HIGH; Commit: `feat(backtest): finalize results and replay`

## Verification and Gate

Every milestone requires focused Ruff/Mypy/tests and targeted anti-future, accounting, deterministic and rule-boundary regression. Gate requires T+1/suspension/limits/tax/actions regressions, no future fills, exact repeated result, all reviews PASS and one `make verify` closure.

## Evidence

- M5.1–M5.10 — PASS in ordered commits `0b751e2`, `349184a`, `614144c`,
  `996ff93`, `cbfa2a7`, `4d27292`, `82e36bf`, `275780e`, `d110191`, `585fc39`.
- Focused Ruff/Mypy/tests/diff checks passed per milestone; all 33 backtest tests
  passed together. Review confirmed deterministic event keys, next-session fills,
  exact accounting, injected-calendar T+1, fail-closed suspension/limits,
  versioned fees, raw-open liquidity/cash/lot constraints, staged/idempotent
  actions, intent-only rebalance, and immutable replay fingerprints.
- Main-Agent Phase Gate `make verify` PASS on 2026-08-24: Ruff PASS, Mypy PASS
  (40 sources), tests PASS (173), evals PASS (1); single complete closure.

## Review decision

- Milestone Reviews M5.1–M5.10: PASS
- Phase 5 Review: PASS
- No future/same-bar fills, adjusted execution prices, Provider/network/broker or
  Phase 6 scope.
- Residual risks: injected rule schedules/references remain trusted inputs; no
  universal execution-price tick quantization; Phase 4 and account position
  models are timeline-gated rather than fully unified; fee audit combines fills
  with the cash ledger.
