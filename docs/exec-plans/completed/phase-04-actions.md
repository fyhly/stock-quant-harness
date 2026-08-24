# Phase 4 ExecPlan — Corporate Actions / Adjustments

Status: COMPLETED

## Objective

以显式事件/生效/可知时间和精确数值语义建模公司行动，生成可追溯复权视图，并保证研究价格、真实交易价格和持仓会计严格分离。

## Ordered task contracts

All tasks depend on the preceding accepted milestone. Allowed scope is `stock_quant.actions`, focused tests/exports/docs and narrowly required integration hooks. Forbidden throughout: Provider/network, Backtest event loop/order matching, broker/live behavior, future corporate-action leakage, adjusted prices as execution prices, or tuning semantics for returns.

### P04-M4.1-T1 — Corporate-action model
- Goal/output: immutable typed dividend, bonus/transfer and rights events with security, announcement/record/ex/effective/pay dates, exact ratios/prices, source/version identity and chronology validation.
- Tests/acceptance: event types, required dates, chronology, Decimal/type validation, deterministic identity; event and effective/availability times are distinct.
- Risk: HIGH; Commit: `feat(actions): add corporate action model`

### P04-M4.2-T1 — Cash dividends
- Goal/output: pure cash entitlement/application calculation with explicit tax policy boundary and payable date.
- Tests/acceptance: ex/pay-date boundaries, eligible quantity, exact cash ledger delta, zero/invalid cases; no false PnL.
- Risk: HIGH; Commit: `feat(actions): handle cash dividends`

### P04-M4.3-T1 — Bonus/transfer shares
- Goal/output: pure quantity/cost-basis adjustment with fractional-share policy and conservation evidence.
- Tests/acceptance: quantity changes, rounding, exact market-value/cost conservation under reference price.
- Risk: HIGH; Commit: `feat(actions): handle bonus share events`

### P04-M4.4-T1 — Rights issues
- Goal/output: explicit participate/decline policy producing cash/share deltas; no implicit election.
- Tests/acceptance: both branches, insufficient cash, ratios/rounding and cost basis; rule is explicit.
- Risk: HIGH; Commit: `feat(actions): model rights issues`

### P04-M4.5-T1 — Adjustment-factor series
- Goal/output: versioned, immutable factor series derived from ordered actions and unadjusted reference prices with full event lineage.
- Tests/acceptance: boundaries, continuity identities, same-day ordering/unsupported inputs, no pre-announcement knowledge leakage.
- Risk: HIGH; Commit: `feat(actions): compute adjustment factors`

### P04-M4.6-T1 — Forward-adjusted research view
- Goal/output: deterministic forward-adjusted bar view labeled research-only.
- Tests/acceptance: formulas/boundaries/lineage and explicit rejection as execution price.
- Risk: HIGH; Commit: `feat(actions): add forward adjusted prices`

### P04-M4.7-T1 — Backward-adjusted research view
- Goal/output: deterministic backward-adjusted research view with separate semantics.
- Tests/acceptance: formulas, base date, continuity, lineage and no execution coercion.
- Risk: HIGH; Commit: `feat(actions): add backward adjusted prices`

### P04-M4.8-T1 — Raw execution-price view
- Goal/output: typed unadjusted execution-price view sourced only from normalized raw DailyBars.
- Tests/acceptance: research views cannot enter execution API; raw OHLC unchanged across actions.
- Risk: HIGH; Commit: `feat(actions): separate execution price semantics`

### P04-M4.9-T1 — Position action application
- Goal/output: pure position/cash transition hooks for dividend, bonus/transfer and rights policies, with idempotent event ledger and accounting audit.
- Tests/acceptance: exact deltas, duplicate application rejection, ordered multi-action case and NAV continuity; no event loop or orders.
- Risk: HIGH; Commit: `feat(actions): apply actions to positions`

## Verification and Gate

Every milestone requires focused Ruff/Mypy/tests plus time-boundary, exact-arithmetic, anti-leakage, determinism and regression checks. Gate requires all reviews PASS, company actions create no artificial PnL, research/execution price types are non-interchangeable, position continuity integration passes, and one `make verify` closure passes.

## Evidence

- M4.1–M4.9 — PASS in ordered commits `4b14849`, `8f4cf5c`, `0b171bf`,
  `ae250a2`, `32b9e0a`, `198c5b6`, `39dc809`, `19a8338`, `c726d08`.
- Focused Ruff/Mypy/tests and diff checks passed at every milestone. Review
  confirmed exact event identity, distinct announcement/record/ex/settlement
  dates, explicit tax/fraction/election policies, atomic same-day factor math,
  knowledge cutoffs, and input-order-independent lineage.
- Forward/backward views are distinct research-only types; the execution API
  accepts only unadjusted RawExecutionPriceView. Position hooks use idempotent
  ledger keys and tested exact cash/quantity/cost/NAV transitions.
- Main-Agent Phase Gate `make verify` PASS on 2026-08-24: Ruff PASS, Mypy PASS
  (29 sources), tests PASS (140), evals PASS (1); single full closure.

## Review decision

- Milestone Reviews M4.1–M4.9: PASS
- Phase 4 Review: PASS
- No Provider/network/order/event-loop/broker or Phase 5 scope.
- Residual risks: date—not intraday—availability; minimal flat-tax and one-stage
  rights settlement policies; no cash-in-lieu/tick quantization; caller must
  supply verified pre-ex raw references and record-date entitlement quantities.
