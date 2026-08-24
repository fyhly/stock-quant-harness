# Phase 7 ExecPlan — Strategy + Portfolio

Status: ACTIVE

## Objective

将带时点/血缘的因子分数确定性转换为受约束目标权重，并通过现有 rebalance intent 接入回测；策略不得接触成交层。

## Ordered task contracts

Allowed: `stock_quant.strategy`, `stock_quant.portfolio`, focused tests/exports/docs and narrow intent integration. Forbidden: Provider/network, fills/orders/execution calls from strategy, RiskEngine implementation (Phase 8), alpha tuning, future features or Phase 8 scope.

### P07-M7.1-T1 — Strategy API
- Goal/output: typed decision-date feature snapshot → ranked selection/score intent contract with universe/config/data lineage; no execution dependency.
- Tests/acceptance: contracts, cutoff/identity alignment, missing/duplicate features, deterministic outputs.
- Risk: HIGH; Commit: `feat(strategy): define strategy api`

### P07-M7.2-T1 — Rank / Top-N
- Goal/output: stable rank/top-N selector with explicit ascending/ties/missing policy and explanation records.
- Tests/acceptance: ranking, ties at boundary, missing values, input-order invariance and reasons.
- Risk: MEDIUM; Commit: `feat(strategy): add rank selection`

### P07-M7.3-T1 — Rebalance schedule
- Goal/output: injected-calendar weekly/monthly schedules producing decision at declared close and next-session order eligibility.
- Tests/acceptance: week/month boundaries, holidays, start/end coverage, no same-day future price.
- Risk: HIGH; Commit: `feat(strategy): add rebalance scheduling`

### P07-M7.4-T1 — Equal weight
- Goal/output: selected securities → exact normalized target weights with explicit cash target/rounding residual.
- Tests/acceptance: weight sum, empty set, cash, deterministic allocation and invalid selection.
- Risk: MEDIUM; Commit: `feat(portfolio): add equal weight`

### P07-M7.5-T1 — Score weight
- Goal/output: nonnegative transformed scores → bounded normalized weights with explicit negative/zero/missing policy.
- Tests/acceptance: signs, normalization, zero total, ordering and precision.
- Risk: HIGH; Commit: `feat(portfolio): add score weighting`

### P07-M7.6-T1 — Basic constraints and integration
- Goal/output: configurable single-name cap, cash floor and gross cap applied deterministically, then emit Phase 5 TargetWeight/rebalance intent; no fills.
- Tests/acceptance: boundaries/infeasible inputs/extremes, residual cash, Strategy→Portfolio→Backtest-intent integration and no execution dependency.
- Risk: HIGH; Commit: `feat(portfolio): add basic constraints`

## Verification and Gate

Focused Ruff/Mypy/tests per milestone plus cutoff, schedule, precision, determinism and layer-boundary regressions. Gate requires full Strategy→Portfolio→rebalance-intent integration, no strategy bypass, all reviews PASS and one `make verify` closure.

## Evidence

Pending implementation and review.
