# Phase 3 ExecPlan — Security Master / Point-in-Time Universe

Status: COMPLETED

## Objective

用显式有效期历史构建可审计的 Security Master 与 Point-in-Time Universe，保留退市/失败样本并阻断当前状态回放历史。

## Ordered task contracts

All tasks depend on the prior accepted milestone, may modify only `stock_quant.universe`, its exports/tests and directly related docs, and must not add Provider/network, corporate actions, backtest/execution, current-state fallback, or Phase 4 behavior.

### P03-M3.1-T1 — Security Master
- Goal/Output: immutable security metadata registry retaining historical and delisted identities; explicit duplicate/conflict handling and as-of-neutral identity lookup.
- Tests/Acceptance: metadata lookup, duplicate/conflict rejection, delisted retention, deterministic order; no current-survivor deletion.
- Risk: HIGH; Commit: `feat(universe): add security master`

### P03-M3.2-T1 — Listing history filter
- Goal/Output: filter identities by injected `ListingLifecycle` at an as-of date.
- Tests/Acceptance: pre-listing/listed/delisted boundaries and retained history; Point-in-Time correct.
- Risk: HIGH; Commit: `feat(universe): add listing history filters`

### P03-M3.3-T1 — Historical ST filter
- Goal/Output: eligibility using injected `STStatusHistory`, with explicit policy and unknown-history fail closed.
- Tests/Acceptance: status transition boundaries and regression against present-ST contamination.
- Risk: HIGH; Commit: `feat(universe): add historical st status`

### P03-M3.4-T1 — Suspension history
- Goal/Output: as-of suspension eligibility from `TradeStatusHistory`, distinct from valuation/fill semantics.
- Tests/Acceptance: suspension/trading transitions and unknown status; feasibility query is explainable.
- Risk: HIGH; Commit: `feat(universe): add suspension history`

### P03-M3.5-T1 — Index membership history
- Goal/Output: immutable half-open `IndexMembership` effective intervals and as-of membership query.
- Tests/Acceptance: entry/exit/boundaries/gaps/overlaps; current constituents cannot backfill history.
- Risk: HIGH; Commit: `feat(universe): add index membership history`

### P03-M3.6-T1 — Industry history
- Goal/Output: effective-dated `IndustryMembership` with explicit taxonomy/version and as-of lookup.
- Tests/Acceptance: changes, gaps, overlaps, taxonomy identity; Point-in-Time classification.
- Risk: HIGH; Commit: `feat(universe): add industry membership history`

### P03-M3.7-T1 — Historical liquidity filter
- Goal/Output: configurable trailing liquidity decision using only bars strictly available by decision cutoff; record window/evidence.
- Tests/Acceptance: thresholds, insufficient/gapped history, future-row rejection/regression, deterministic result.
- Risk: HIGH; Commit: `feat(universe): add liquidity filters`

### P03-M3.8-T1 — Universe Engine
- Goal/Output: compose listing/ST/suspension/index/liquidity rules for a date and return eligible identities plus ordered typed exclusion reasons.
- Tests/Acceptance: historical snapshots, all rule branches, missing facts fail closed, no survivors/current-state leakage, deterministic composition.
- Risk: HIGH; Commit: `feat(universe): implement point-in-time universe`

### P03-M3.9-T1 — Universe Snapshot
- Goal/Output: immutable content-addressed local snapshot containing as-of time, included set, exclusions, rule version, upstream artifact/data identities and code/config identity.
- Tests/Acceptance: round-trip/reproducibility, atomic no-overwrite, tamper/missing-version rejection and full traceability.
- Risk: HIGH; Commit: `feat(universe): persist universe snapshots`

## Verification and gate

Each milestone requires focused Ruff/Mypy/tests plus boundary, missing-history, anti-leakage and deterministic regressions. Phase Gate requires all nine Reviews PASS, a historical-date integration proving only then-valid securities are visible, explicit retained delisted securities and historical index/ST behavior, and one `make verify` PASS.

## Boundary

All inputs are injected local facts/artifacts. No network, Provider, broker/account/order side effect, silent current-state fallback, or deletion of excluded/failed identities.

## Evidence

- M3.1–M3.9 — PASS in ordered commits `68d0c27`, `d2563bd`, `e567966`,
  `a0d6516`, `bd2cc69`, `3048c9e`, `173c601`, `65ba1dd`, `99714e3`.
  Each passed focused Ruff/Mypy/tests and diff checks (32 milestone tests total).
- Review confirmed retained delisted identities, effective-dated listing/ST/
  suspension/index/industry facts, missing-history fail-closed behavior, strict
  pre-decision liquidity windows, deterministic typed exclusion reasons, and
  content-addressed atomic snapshots with rule/upstream/code/config identities.
- Historical integration proves later ST/delisting facts do not contaminate an
  earlier universe and later index constituents do not backfill history.
- Main-Agent Phase Gate `make verify` PASS on 2026-08-24: Ruff PASS, Mypy PASS
  (20 sources), tests PASS (104), evals PASS (1); single full closure.

## Review decision

- Milestone Reviews M3.1–M3.9: PASS
- Phase 3 Review: PASS
- No Provider/network/backtest/Phase 4 scope or live side effect.
- Residual risks: index coverage completeness remains an explicit trusted input;
  snapshot records canonical upstream IDs but a cross-store resolver belongs to
  later integration; universe `as_of` currently has trading-date granularity.
