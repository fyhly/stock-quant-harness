# Phase 6 ExecPlan — Features / Factors

Status: ACTIVE

## Objective

建立带显式 decision/availability 时间的 Feature API，并实现第一批可复现因子族；任何值只能使用当时已知的本地数据。

## Ordered task contracts

All tasks depend on the prior accepted milestone. Allowed: `stock_quant.features`, focused tests/exports/docs/config. Forbidden: Provider/network, strategy/portfolio/backtest changes, full-sample fitting, future labels in inputs, current/restated financial backfill, or Phase 7 work.

### P06-M6.1-T1 — Feature API
- Goal/output: typed time-series/cross-sectional request, observation with event/availability time, decision cutoff, result metadata/lineage and deterministic feature contract.
- Tests/acceptance: contract/type/ordering, cutoff enforcement, missing/duplicate facts fail explicitly.
- Risk: HIGH; Commit: `feat(features): define feature api`

### P06-M6.2-T1 — Momentum
- Goal/output: exact 20/60/120-session trailing returns from unadjusted or explicitly declared research views, excluding decision-day unavailable close.
- Tests/acceptance: window boundaries, gaps, cutoff, scale invariance, no future rows.
- Risk: HIGH; Commit: `feat(factors): add momentum factors`

### P06-M6.3-T1 — Reversal
- Goal/output: 5/10-session short-term reversal with same cutoff/window semantics.
- Tests/acceptance: formula, boundaries, insufficient/gapped history and no future data.
- Risk: HIGH; Commit: `feat(factors): add reversal factors`

### P06-M6.4-T1 — Volatility
- Goal/output: realized and downside volatility over declared trailing sessions with explicit annualization/missing policy.
- Tests/acceptance: formula/constant/negative returns, minimum observations, cutoff/determinism.
- Risk: HIGH; Commit: `feat(factors): add volatility factors`

### P06-M6.5-T1 — Value
- Goal/output: PE/PB/PS/earnings-yield from effective-dated valuation/fundamental observations selected by announcement availability, preserving negative/undefined semantics.
- Tests/acceptance: announcement boundary, revisions, negative/zero denominators, stale/missing data and future announcement rejection.
- Risk: HIGH; Commit: `feat(factors): add value factors`

### P06-M6.6-T1 — Quality
- Goal/output: ROE, margin and cash-flow-quality using point-in-time statements with report period and announcement/revision availability.
- Tests/acceptance: statement alignment, announcement boundary, restatement leakage regression, invalid denominators/missing facts.
- Risk: HIGH; Commit: `feat(factors): add quality factors`

### P06-M6.7-T1 — Size/Liquidity
- Goal/output: market/float cap and trailing turnover features with explicit shares/version and session window identities.
- Tests/acceptance: exact formula, coverage, cutoff, stale shares and future bars/shares rejection.
- Risk: HIGH; Commit: `feat(factors): add size liquidity factors`

### P06-M6.8-T1 — Cross-sectional transforms
- Goal/output: per-date winsorize, standardize and rank with explicit missing/tie/constant policies and fitted-date metadata.
- Tests/acceptance: full cross-section, missing/ties/outliers/constants, input-order determinism; never fit across dates/full sample.
- Risk: HIGH; Commit: `feat(factors): add cross sectional transforms`

## Verification and Gate

Each milestone: focused Ruff/Mypy/tests plus cutoff, leakage, window, missing and deterministic regressions. Gate: all factor families run, financial announcement/revision leakage tests pass, no full-sample cross-sectional fit, all reviews PASS and one `make verify` closure.

## Evidence

Pending implementation and review.
