# V1 Final Audit ExecPlan

Status: COMPLETED

## Objective

审计 Phase 0–16 的工程完整性、数据可信度、Point-in-Time、幸存者偏差、公司行动、A 股回测、研究/OOS、Portfolio/Risk、Daily Research、Harness/Git/tests/evals/verify 与 OFFLINE 边界。结果只有 PASS 才完成 V1。

## Audit task contracts

### V1-A1 — Repository / Harness / Git
- Allowed: read-only inspection, audit docs/evals and bounded fixes if a finding is confirmed.
- Checks: all 17 completed plans and reviews, no active Phase, milestone commits, main/remote state, commands/failure propagation, dependency pins, untracked/user material excluded.
- Acceptance: complete trace and no skipped Phase/Milestone.
- Risk: MEDIUM

### V1-A2 — Data / PIT / survivorship
- Checks: immutable Raw, normalized/hash/lineage, announcement/revision cutoffs, retained delisted identities, historical ST/index/industry, cutoff windows and no current fallback.
- Acceptance: targeted anti-leakage tests/evals and traceable real sample PASS.
- Risk: HIGH

### V1-A3 — Corporate actions / Backtest realism
- Checks: ex/settlement separation, adjustment/execution type isolation, NAV continuity, timeline/no same-bar fills, T+1, suspension, limits, costs, liquidity, replay/accounting.
- Acceptance: targeted regression/eval PASS with explicit simplifications.
- Risk: HIGH

### V1-A4 — Research / OOS / Portfolio / Risk
- Checks: formal manifests/artifacts/replay, failure retention, fixed benchmarks, cross-sectional alignment, frozen train/validation/OOS, Candidate Gate, PIT neutralization, RiskEngine mandatory and infeasible fail closed, costs/turnover visible.
- Acceptance: no OOS selection path or Risk bypass; targeted audit PASS.
- Risk: HIGH

### V1-A5 — Daily / OFFLINE / safety
- Checks: staged update, quality zero-downstream, PIT refresh, reason completeness, RiskDecision-only output, manual-decision report, offline replay; scan production for broker/account/order/client automation/secrets and hidden runtime network.
- Acceptance: no real-trading side effect and fatal data never yields normal signal.
- Risk: CRITICAL

### V1-A6 — Complete verification and audit report
- Output: `docs/audits/V1_FINAL_AUDIT.md` with PASS/CONDITIONAL PASS/FAIL per dimension, exact commands/results, findings/remediation, residual limitations, frozen-core decision and final outcome.
- Checks: one complete `make verify`, targeted semantic evals, deterministic real E2E fingerprint, clean tracked worktree, main merge/push only after final PASS.
- Acceptance: final outcome PASS; otherwise bounded fixes and re-audit.
- Risk: HIGH

## Evidence

- V1-A1 — PASS: all 17 Phase plans are completed in order, every referenced
  commit resolves, dependencies are pinned, and `main == origin/main` at audit
  base `423da8f`.
- V1-A2–A5 — PASS: high-risk targeted suite 275 passed; new cross-module
  semantic/safety evals cover PIT/survivorship, action/execution separation,
  OOS context isolation, Daily fatal zero-downstream, frozen real replay,
  hidden network/trading capability and secret patterns.
- Real E2E replay remained exactly
  `b6b4be7b4917c65f6ba03cca6a4a1f231266034dbc39803a80dfa3fc2fca1e96`
  and every fill follows the decision date.
- Initial complete closure exposed collection-order dependence in the legacy
  bootstrap eval. Bounded fix `5535c55` stabilized the declared root API check
  without changing product behavior; no test was removed or weakened.
- Final audit closure: Ruff PASS, Mypy PASS (121 sources), tests PASS (325),
  evals PASS (6).
- Audit report: `docs/audits/V1_FINAL_AUDIT.md`.

## Review decision

- V1-A1–V1-A6: PASS
- V1 Final Audit: PASS
- Core decision: Phase 0–16 V1 is frozen; future work must enter a separately
  reviewed Research Loop plan and preserve all safety/PIT boundaries.
