# Phase 0 ExecPlan — Harness / 工程基座

Status: COMPLETED

## Objective

建立可导入、可测试、可审计且严格保持 OFFLINE 边界的 Python 工程基座，为 Phase 1 的 A 股领域模型提供稳定入口。

## Sequence and task contracts

### P00-M0.1-T1 — Repository skeleton

- Phase/Milestone: Phase 0 / M0.1
- Goal: 创建 `src/stock_quant`、`tests`、`evals`、`docs`、`configs`、`scripts` 和固定 Python/依赖的 `pyproject.toml`。
- Dependencies: none
- Allowed: repository skeleton, package metadata, minimal import smoke test, README bootstrap documentation
- Forbidden: business models, network/data providers, broker/live execution, later-phase implementation
- Input: Phase 0 milestone specification
- Output: importable package and skeleton
- Tests: package import and minimal smoke test
- Acceptance: clear layout, no premature business logic, Python/dependencies constrained
- Risk: LOW
- Commit: `chore: bootstrap repository structure`

### P00-M0.2-T1 — Agent constitution

- Phase/Milestone: Phase 0 / M0.2
- Goal: 创建项目 `AGENTS.md`，固化使命、风险等级、OFFLINE 边界和 A 股防泄漏约束。
- Dependencies: M0.1
- Allowed: `AGENTS.md`
- Forbidden: runtime code and weakening safety constraints
- Input: Harness standards
- Output: agent operating rules
- Tests: structural/manual rules review
- Acceptance: all required constitutional sections present
- Risk: MEDIUM (safety policy)
- Commit: `docs: add agent operating rules`

### P00-M0.3-T1 — Architecture

- Phase/Milestone: Phase 0 / M0.3
- Goal: 定义 Data→Universe→Factors→Portfolio→Backtest→Report 分层及显式时间语义。
- Dependencies: M0.2
- Allowed: `ARCHITECTURE.md`
- Forbidden: implementation and live-trading architecture
- Input: roadmap and agent constitution
- Output: architecture document
- Tests: consistency/manual review
- Acceptance: responsibilities, offline separation, time semantics explicit
- Risk: MEDIUM
- Commit: `docs: define system architecture`

### P00-M0.4-T1 — ExecPlan lifecycle

- Phase/Milestone: Phase 0 / M0.4
- Goal: 建立 active/queued/completed 生命周期和模板。
- Dependencies: M0.3
- Allowed: `PLANS.md`, `docs/exec-plans/**`
- Forbidden: treating queued work as authorization
- Input: orchestration standard
- Output: lifecycle documentation and directories
- Tests: path/template checks
- Acceptance: only one active Platform Phase; queued is not authorized
- Risk: LOW
- Commit: `docs: add execplan lifecycle`

### P00-M0.5-T1 — Development lifecycle

- Phase/Milestone: Phase 0 / M0.5
- Goal: 定义短分支、小 Commit、Review 与 test/eval/verify 完成标准。
- Dependencies: M0.4
- Allowed: `docs/DEVELOPMENT_LIFECYCLE.md`
- Forbidden: runtime behavior changes
- Input: Git and verification standards
- Output: lifecycle documentation
- Tests: workflow/manual review
- Acceptance: branch, commit, review and gate rules explicit
- Risk: LOW
- Commit: `docs: add development lifecycle`

### P00-M0.6-T1 — Verification foundation

- Phase/Milestone: Phase 0 / M0.6
- Goal: 提供失败返回非零的 `make test`, `make eval`, `make verify`，其中 verify 聚合 lint/type/test/eval。
- Dependencies: M0.5
- Allowed: Makefile, tool configuration, tests/evals/scripts needed by the commands
- Forbidden: deleting tests, suppressing failures, business implementation
- Input: repository skeleton and minimum-sufficient-verification standard
- Output: unified verification commands
- Tests: run each unique verification path without redundant full runs
- Acceptance: all commands work; verify covers lint/type/test/eval
- Risk: LOW
- Commit: `build: add verification commands`

## Offline boundary

V1 is research-only. No brokerage/account connection, browser/client automation, order submission, secrets handling, or live execution side effect is permitted. External data, when introduced in Phase 9, must first land as immutable Raw Artifacts. Human users retain every final trading decision.

## Phase gate

- All M0.1–M0.6 reviews are PASS.
- Package imports and smoke tests pass.
- `make test`, `make eval`, and `make verify` are represented by one non-duplicative full verification closure.
- Evidence is recorded in this ExecPlan before it moves to `completed/`.
- Phase 1 may start only after this gate passes and its ExecPlan is explicitly created.

## Evidence

- M0.1 — PASS: commit `63ad60f`; import smoke test passed; skeleton and
  constrained Python metadata reviewed with no Phase 1 business logic.
- M0.2 — PASS: commit `f96a8d7`; constitution contains mission, risk levels,
  OFFLINE/CRITICAL stop boundary, and A-share temporal/leakage invariants.
- M0.3 — PASS: commit `fb72bd6`; architecture responsibilities, dependency
  direction, research/execution separation, and explicit time semantics reviewed.
- M0.4 — PASS: commit `f9894dd`; active/queued/completed lifecycle and template
  exist; exactly one Platform plan was active; queued work is explicitly not
  authorization.
- M0.5 — PASS: commit `69c1d32`; short branches, small commits, review,
  minimum-sufficient verification, and definition of done are explicit.
- M0.6 — PASS: commit `090426b`; `make verify` aggregates Ruff, Mypy, tests,
  and evals and propagates failure. Executor observed an initial nonzero type
  failure before adding `py.typed`, then passed the corrected closure.
- Main-Agent Phase Gate rerun: `make verify` PASS on 2026-08-24; Ruff PASS,
  Mypy PASS (1 source), tests PASS (1), evals PASS (1). This single run is the
  required non-duplicative full closure because `verify` includes every public
  check.
- Scope review: six ordered milestone commits, no later-phase implementation,
  no live/broker side effect, and the extracted startup pack remains untracked.

## Review decision

- Milestone Reviews M0.1–M0.6: PASS
- Phase 0 Review: PASS
- Residual risk: local verification requires the pinned development tools to be
  installed in `.venv`; runtime dependencies are empty and verification has no
  network dependency.
- Phase 1 entry condition: satisfied only after this completed plan is archived
  and an explicit Phase 1 active ExecPlan is created.
