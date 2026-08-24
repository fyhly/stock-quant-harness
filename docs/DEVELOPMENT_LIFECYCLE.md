# Development Lifecycle

## Branches and scope

Platform work uses one short-lived branch per authorized phase, named
`phase/NN-topic`. Research work, only after its capability gate, uses
`research/RNNN-topic`. A branch follows the active ExecPlan in dependency order
and contains no speculative next-phase work or unrelated cleanup.

Before editing, inspect the worktree and preserve user-owned changes. Never
rewrite shared history or use destructive cleanup to make a review appear tidy.

## Commits

Each milestone produces at least one small logical commit after its focused
verification passes. A commit should be independently reviewable and revertible,
name the domain change, and include its tests or documentation. Do not mix
formatting, refactoring, generated artifacts, or later tasks into it. Suggested
forms are `chore:`, `docs:`, `build:`, `test:`, and scoped behavioral messages.

## Minimum sufficient verification

Verification strength is proportional to change risk:

- Task: run the smallest directly relevant test, lint, type, structural, or
  documentation check.
- Milestone: run affected-module tests and only necessary integration,
  regression, leakage, determinism, or eval checks.
- High-risk financial semantics: add targeted regression, integration,
  anti-leakage, and reproducibility evidence; escalate ambiguous design.
- Phase gate: run one complete, non-duplicative closure. When `make verify`
  already aggregates lint, type, test, and eval, its successful run supplies the
  full closure rather than rerunning equivalent commands for formality.
- V1 Final Audit: run the complete final verification and semantic audits.

Commands must return nonzero on failure. Tests may not be deleted, skipped, or
weakened to pass a gate, and production semantics may not be tuned to a desired
research result.

## Review

Milestone review checks the task contract, diff scope, tests, documentation,
OFFLINE boundary, temporal invariants, commit granularity, and residual risk.
It records `PASS`, `CONDITIONAL PASS`, or `FAIL` in the active ExecPlan.

Phase review checks every milestone decision, the full verification closure,
actual ExecPlan evidence, and prerequisite status for the next phase. Reviewers
must distinguish commands actually run from planned checks. A conditional or
failed review creates bounded remediation and blocks dependent work.

## Definition of done

A task or milestone is done only when:

- its authorized output and necessary documentation exist;
- focused tests/evals/checks pass and their rationale is reported;
- no forbidden or unrelated changes are included;
- review records a decision and known risks;
- the logical commit is complete and traceable to its task contract.

A phase is done only when all milestones pass, the non-duplicative full gate
passes, evidence is recorded in the ExecPlan, and the plan is moved to
`completed/`. Completion does not itself authorize the next queued phase.
