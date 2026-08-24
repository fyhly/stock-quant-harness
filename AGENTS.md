# Agent Operating Rules

These rules apply to the entire repository. A more local `AGENTS.md` may add
constraints, but it may not weaken this constitution.

## Mission

Build a reproducible, auditable, offline-first A-share quantitative research
system. Research quality, temporal correctness, and explicit uncertainty take
priority over attractive backtest results or delivery speed.

## Operating model

- Follow the authorized active ExecPlan in milestone and task order.
- Do not treat queued plans, roadmap items, or research ideas as authorization.
- Keep changes small, reviewable, reversible, and within the current task.
- Preserve failing evidence. Never delete tests or relax a financial invariant
  to obtain a passing result.
- Record the tests, evaluations, assumptions, and residual risks used for each
  acceptance decision.

## Risk levels

- **LOW**: documentation, scaffolding, and non-behavioral tooling. Use focused
  structural or smoke checks.
- **MEDIUM**: local behavior, data transformations, interfaces, or workflow
  policy. Require focused tests and regression coverage for affected paths.
- **HIGH**: point-in-time semantics, universe history, corporate actions,
  adjustment, matching, fees, T+1, limits, suspension, portfolio/risk, or OOS.
  Escalate design decisions, add leakage/regression/integration checks, and
  require explicit review before acceptance.
- **CRITICAL**: any proposal involving credentials, accounts, brokers, order
  submission, or live execution. It is forbidden in V1 and must stop closed.

## OFFLINE boundary

V1 is research-only and offline by default.

- No brokerage or account connection, browser/client automation, order
  submission, live trading, secrets handling, or trading side effect.
- No component may imply that an output is an executable trading instruction.
  Human users retain every final trading decision.
- External data, when explicitly authorized in a later phase, must first land
  as an immutable Raw Artifact with provenance. Downstream research consumes
  validated local artifacts, never an implicit live response.
- Network access is not an acceptable hidden dependency of tests, evaluations,
  backtests, reports, or daily research. Missing required local inputs must fail
  closed with a clear error.

## A-share temporal and anti-leakage invariants

- Every observation has explicit event time, availability/announcement time,
  effective time, and ingestion/version metadata where applicable.
- A decision at time `t` may use only information demonstrably available by
  `t`. Revision history is preserved; later restatements never overwrite the
  historical view used by an earlier decision.
- Universe membership is point-in-time. Current constituents or current
  security status must never be projected backward; delisted and suspended
  securities remain represented when historically relevant.
- Corporate actions and price adjustments are versioned and applied with
  explicit ex-date/pay-date semantics. Adjusted prices must not leak future
  actions into earlier decisions.
- Features, labels, fills, fees, and reports declare their time convention.
  Signals cannot execute on data unavailable at the modeled decision time.
- Backtests must explicitly model applicable A-share constraints, including
  trading calendars, T+1, suspension, price limits, lot sizes, fees, and taxes.
  Unsupported rules fail closed rather than silently assuming frictionless
  execution.
- Train/validation/test and walk-forward windows are chronological and isolated.
  Preprocessing is fitted inside the relevant training window; OOS results are
  never used to tune the evaluated candidate.
- Deterministic inputs and configuration must produce reproducible outputs with
  traceable code, data, and parameter versions.

## Verification and completion

Use minimum sufficient verification for tasks and milestones, reserving the
complete `make verify` closure for phase gates and final audit. A task is done
only when its artifact, focused checks, documentation, review evidence, and
known risks are recorded. Financial-semantic uncertainty is a reason to stop
and escalate, not to guess.
