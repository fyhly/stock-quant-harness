# Phase 14 ExecPlan — Walk-Forward / OOS

Status: COMPLETED

## Objective

建立严格隔离、可审计、确定的 Train→Validation→Frozen Selection→OOS 与 Walk-Forward 系统，并以自动防泄漏 Gate 控制 Candidate 升级。

## Ordered task contracts

Allowed: `stock_quant.oos`, OOS configs/tests/reports and research adapters. Forbidden: Provider/network, OOS-informed selection, post-hoc parameter changes, overlapping windows, hidden failed windows, core semantic changes or Phase 15.

### P14-M14.1-T1 — Time-window model
- Output: immutable half-open Train/Validation/OOS window sets with chronology, gap/embargo and no-overlap validation.
- Tests: all boundaries, adjacency/gaps, overlap/reversal and deterministic identity.
- Risk: HIGH; Commit: `feat(oos): add time windows`

### P14-M14.2-T1 — Train runner
- Output: runner/context exposing only train-bounded data and fitted artifact/config identities.
- Tests: outside-train access rejected, failure retained, repeatability.
- Risk: HIGH; Commit: `feat(oos): add train runner`

### P14-M14.3-T1 — Validation selection
- Output: predefined finite parameter-space evaluation, deterministic selection rule/ties and immutable selection record.
- Tests: fixed space, train/validation-only access, complete candidates/failures and audit trail.
- Risk: HIGH; Commit: `feat(oos): add validation stage`

### P14-M14.4-T1 — OOS runner
- Output: run frozen selected configuration against OOS-only context, prohibiting selection callbacks/results access.
- Tests: OOS cannot alter selection, identity drift/future access fail, exact repeat.
- Risk: HIGH; Commit: `feat(oos): add oos runner`

### P14-M14.5-T1 — Walk-forward engine
- Output: deterministic ordered multi-window orchestration with independent fit/select/freeze/OOS records.
- Tests: multiple windows, per-window isolation, failures retained and rerun equality.
- Risk: HIGH; Commit: `feat(oos): add walk forward runner`

### P14-M14.6-T1 — Stitch OOS results
- Output: continuous non-overlapping OOS equity/returns with explicit boundary/cash convention and provenance.
- Tests: duplicates/gaps/order, no double count, compounding/reconciliation.
- Risk: HIGH; Commit: `feat(oos): stitch oos results`

### P14-M14.7-T1 — Stability analytics
- Output: parameter/factor/window stability summary including every failed/negative window.
- Tests: aggregation/formulas, failures visible, missing/constant/extreme cases.
- Risk: HIGH; Commit: `feat(oos): add stability analytics`

### P14-M14.8-T1 — Candidate Gate
- Output: predeclared criteria and typed REJECT/EXPERIMENTAL/PROMISING/CANDIDATE decision requiring complete isolated OOS evidence.
- Tests: P14-before prohibition, OOS leakage/failed window/identity drift rejection, deterministic criteria and research-only report.
- Risk: HIGH; Commit: `docs: define candidate gate`

## Verification and Gate

Focused Ruff/Mypy/tests plus automated forbidden-access, overlap, freeze, failure-retention and determinism regressions. Gate requires OOS never participates in selection, Candidate only through complete evidence, all Reviews PASS and one `make verify` closure.

## Evidence

- M14.1–M14.8 — PASS in commits `aad49c0`, `cef2620`, `650156d`,
  `639ebeb`, `1bbd072`, `174fb76`, `47f85c3`, `10e5c9b`; focused OOS tests
  plus Ruff/Mypy passed.
- Review confirmed half-open isolated windows, predefined finite selection,
  frozen configs, OOS-only contexts, non-overlapping walk-forward/stitching,
  complete stability failures and fail-closed Candidate criteria.
- Gate review found all-failed validation lost per-candidate detail. Fix
  `d762938` retains ordered full evaluations and parameter-space identity while
  forbidding selection/OOS execution.
- Main-Agent Phase Gate `make verify` PASS on 2026-08-24: Ruff PASS, Mypy PASS
  (105 sources), tests PASS (297), evals PASS (1).

## Review decision

- Milestone Reviews M14.1–M14.8: PASS after Gate remediation
- Phase 14 Review: PASS
- Residual: Python callbacks could close over external data, so Candidate Gate
  also requires explicit context-isolation audit evidence; expected dates are
  supplied by the PIT calendar.
