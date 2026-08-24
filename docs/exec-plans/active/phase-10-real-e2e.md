# Phase 10 ExecPlan — First Real A-share E2E Backtest

Status: ACTIVE

## Objective

用小型、冻结、可审计的真实 A 股公开数据串通 Raw→Normalized→Universe→Feature→Strategy→Portfolio→Risk→Backtest，并生成可重复审计报告。

## Data decision

`TUSHARE_TOKEN` is absent. M10.1 may explicitly acquire a bounded unadjusted daily sample from a public HTTPS A-share market-data response with source URL/query/fetch time/hash/schema recorded. Exact bytes must land Raw before parsing; committed/frozen artifacts make all later work offline. Values may not be synthesized or silently corrected.

## Ordered task contracts

### P10-M10.1-T1 — Frozen real-data sample
- Allowed: explicit one-time HTTPS acquisition script/run, `tests/fixtures/real`, manifests, Raw/normalized/quality artifacts and tests/docs.
- Forbidden: secrets, adjusted execution prices, fabricated rows, untracked manual edits, network in tests or subsequent pipeline.
- Output: representative Shanghai/Shenzhen securities and bounded dates, immutable raw hashes, normalized Parquet/manifests and quality report.
- Tests/acceptance: raw trace/hash, schema/units, quality, frozen version and offline reload.
- Risk: HIGH; Commit: `test(e2e): add frozen real-data sample`

### P10-M10.2-T1 — Universe closure
- Goal/output: historical master/status/index facts explicitly frozen for sample coverage and reproducible UniverseSnapshots with exclusions.
- Tests/acceptance: retained identities, PIT snapshot dates, no current-state/survivor backfill and upstream identities.
- Risk: HIGH; Commit: `feat(e2e): wire real universe pipeline`

### P10-M10.3-T1 — Feature closure
- Goal/output: momentum and another feasible baseline feature from frozen bars using cutoff/session semantics.
- Tests/acceptance: artifact lineage, cutoff/no-leakage and deterministic recomputation.
- Risk: HIGH; Commit: `feat(e2e): wire feature pipeline`

### P10-M10.4-T1 — Strategy/Portfolio/Risk closure
- Goal/output: scheduled rank selection → portfolio → RiskDecision → rebalance intents with fixed config.
- Tests/acceptance: sums/constraints/PIT sectors, no bypass, deterministic targets.
- Risk: HIGH; Commit: `feat(e2e): wire strategy portfolio pipeline`

### P10-M10.5-T1 — Backtest closure
- Goal/output: offline deterministic run using next-session raw opens, constraints/costs and complete BacktestResult.
- Tests/acceptance: repeat exact fingerprint, no future fill, accounting identity and frozen expected outputs.
- Risk: HIGH; Commit: `feat(e2e): complete first real backtest`

### P10-M10.6-T1 — Audit report
- Goal/output: Phase 10 report with source/raw/data/Git/config identities, run fingerprint, quality/results and explicit limitations/research-only label.
- Tests/acceptance: trace links/fields and offline render/read.
- Risk: MEDIUM; Commit: `docs: document first real backtest`

## Verification and Gate

Focused checks per milestone. Gate requires a complete offline real-data pipeline, exact repeatability, raw/data/config/Git traceability, no hidden network and one `make verify` closure.

## Evidence

Pending implementation and review.
