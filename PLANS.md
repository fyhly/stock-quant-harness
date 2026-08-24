# ExecPlan Lifecycle

ExecPlans are the repository's authorization and evidence record for platform
work. Roadmaps describe intent; only the single plan under `active/` authorizes
implementation.

## States

- `docs/exec-plans/queued/`: proposed future work. Queued plans are not
  authorized and must not be implemented.
- `docs/exec-plans/active/`: authorized work in progress. There must be exactly
  one active Platform Phase plan while platform work is underway.
- `docs/exec-plans/completed/`: accepted, immutable historical plans whose phase
  gate evidence and review decision are complete.

Research plans, when later authorized by the capability gate, must be clearly
identified as Research Track plans and cannot displace or authorize a second
active Platform Phase.

## Transitions

1. Create a plan from `docs/exec-plans/TEMPLATE.md` in `queued/`.
2. Review its scope, dependencies, task contracts, risks, verification, and
   OFFLINE compliance. Queuing alone grants no permission to execute.
3. After the prior Platform Phase gate passes, explicitly move one reviewed
   Platform plan to `active/` and mark it `ACTIVE`.
4. Execute milestones in order. Append actual evidence and PASS, CONDITIONAL
   PASS, or FAIL decisions; do not rewrite intended checks as if they ran.
5. On PASS of every milestone and the phase gate, mark the plan `COMPLETED` and
   move it to `completed/` in the acceptance commit.
6. A CONDITIONAL PASS or FAIL remains active until its named remediation and
   re-verification are complete. It does not authorize the next phase.

Plan moves use Git history so authorization and acceptance remain auditable.
Completed evidence is corrected only by an explicit follow-up record, never
silently rewritten.

## Required plan content

Every plan states objective, sequence, per-task contract, allowed and forbidden
scope, dependencies, risk, verification, phase gate, evidence, and review
decision. Task contracts include task ID, phase, milestone, inputs, outputs,
tests, acceptance criteria, and suggested commit.
