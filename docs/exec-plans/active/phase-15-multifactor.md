# Phase 15 ExecPlan — Multi-factor Portfolio

Status: ACTIVE

## Objective

建立可解释、PIT、可复现的多因子组合与中性化，并将风险、换手及成本压力透明集成到组合候选。

## Ordered task contracts

Allowed: `stock_quant.multifactor`, Portfolio/Risk adapters, configs/tests/reports. Forbidden: Provider/network, current industry/size backfill, RiskEngine bypass, opaque optimizer, cost hiding/tuning, real orders or Phase 16.

### P15-M15.1-T1 — Factor combination
- Output: aligned per-date factor matrix, explicit weights/signs/missing policy and deterministic composite scores with lineage.
- Tests: weights/alignment/missing/constants/input order and no cross-date leakage.
- Risk: HIGH; Commit: `feat(portfolio): add factor combination`

### P15-M15.2-T1 — Neutralization
- Output: per-date industry demeaning and size residualization using PIT classifications/exposures with method/version evidence.
- Tests: historical industry change/gap, exposure alignment, singular/constant/extreme cases and no full-sample fit.
- Risk: HIGH; Commit: `feat(portfolio): add neutralization`

### P15-M15.3-T1 — Equal/score baselines
- Output: reproducible multi-factor top-N equal and score-weight baselines with config identities and complete candidates.
- Tests: selection/weights/precision/determinism/failure cases.
- Risk: MEDIUM; Commit: `feat(portfolio): add baseline allocators`

### P15-M15.4-T1 — Risk constraints
- Output: MultiFactor candidate → existing RiskRequest/Decision → approved intent, with PIT sectors and no bypass.
- Tests: name/sector/cash/gross/turnover extremes, infeasible fail closed and integration identity.
- Risk: HIGH; Commit: `feat(portfolio): integrate risk constraints`

### P15-M15.5-T1 — Turnover control
- Output: explicit turnover-aware rebalance using current weights, configured cap and audit of desired/approved turnover.
- Tests: zero/partial/full caps, exits/cash/precision and deterministic residual.
- Risk: HIGH; Commit: `feat(portfolio): add turnover control`

### P15-M15.6-T1 — Cost sensitivity
- Output: predeclared multi-level commission/tax/slippage stress results/report retaining turnover, gross/net metrics, failures and all levels.
- Tests: exact cost arithmetic, monotonicity under identical fills, no hidden cost, full-level reconciliation and research-only report.
- Risk: HIGH; Commit: `feat(portfolio): add cost stress tests`

## Verification and Gate

Focused Ruff/Mypy/tests plus PIT, fit-scope, arithmetic, constraint, turnover and all-cost-level regressions. Gate requires every portfolio passes RiskEngine, cost/turnover transparent, all Reviews PASS and one `make verify` closure.

## Evidence

Pending implementation and review.
