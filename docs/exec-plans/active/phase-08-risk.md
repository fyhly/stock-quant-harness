# Phase 8 ExecPlan — Risk Engine

Status: ACTIVE

## Objective

建立独立、确定、可解释且不可绕过的 RiskEngine，将目标组合约束为安全研究意图，并对历史行业和极端输入 fail closed。

## Ordered task contracts

Allowed: `stock_quant.risk`, focused tests/exports/docs and narrow Portfolio integration. Forbidden: Provider/network, optimization solvers, fills/execution/broker, current industry backfill, risk bypass, return tuning or Phase 9.

### P08-M8.1-T1 — Risk API
- Goal/output: typed RiskRequest/Decision with as-of, proposed/current weights, PIT classifications, config/upstream identities, ordered adjustments/rejections and output intent.
- Tests/acceptance: contract/alignment/identity/determinism, all portfolio outputs routed through engine integration.
- Risk: HIGH; Commit: `feat(risk): define risk engine`

### P08-M8.2-T1 — Single-name limits
- Goal/output: exact configurable cap with deterministic clipping and cash residual.
- Tests/acceptance: cap/boundaries/extremes/input order; no uncontrolled weight.
- Risk: HIGH; Commit: `feat(risk): add single name limits`

### P08-M8.3-T1 — Sector limits
- Goal/output: cap aggregate historical-industry exposures with deterministic allocation and explicit missing/gap rejection.
- Tests/acceptance: sector excess, PIT change, missing history, multiple names/ties and current-classification leakage.
- Risk: HIGH; Commit: `feat(risk): add sector limits`

### P08-M8.4-T1 — Turnover cap
- Goal/output: constrain one-way turnover versus current weights with deterministic proportional transition and audit.
- Tests/acceptance: zero/full/partial cap, buys/sells/cash, formula/precision/extremes.
- Risk: HIGH; Commit: `feat(risk): add turnover limits`

### P08-M8.5-T1 — Cash and exposure limits
- Goal/output: enforce cash floor and gross/long exposure cap after all adjustments, preserving explicit residual cash.
- Tests/acceptance: over-allocation, empty/extreme/infeasible configurations, sums and deterministic scaling.
- Risk: HIGH; Commit: `feat(risk): add cash and exposure limits`

### P08-M8.6-T1 — Risk budgets and integration
- Goal/output: simple explicit per-name/sector risk-budget data model (no optimizer) plus fixed RiskEngine pipeline and Portfolio→Risk→RebalanceIntent integration.
- Tests/acceptance: budget sums/bounds, every constraint order, extreme input cannot create uncontrolled positions, no bypass path.
- Risk: HIGH; Commit: `feat(risk): add risk budgets`

## Verification and Gate

Focused Ruff/Mypy/tests plus PIT industry, arithmetic, infeasible, ordering and deterministic regressions. Gate requires all target weights pass RiskEngine, extreme inputs safe, all Reviews PASS and one `make verify` closure.

## Evidence

Pending implementation and review.
