- created: 2026-07-25
- created_by: Sebastien Lambla
- created_during: orchestrator session (echo-loop fix round)

## Blockers

- None — the design is ruled (Decision-088); [[ingest-echo-loop]]'s fix is
  merged and proven (local pull 0 after a full mirror push).

## Questions

- ~~Where the task-id field lives concretely.~~ REFINED by operator
  (2026-07-25): it need not be hidden — PUBLIC is preferred, useful to the
  manager. Concretely: a visible `id:<task-id>` label (or public Project
  field); pick whichever the API matches cheapest at build time.

## Findings

- Decision-088 is the spec: task id as the hidden binding field; sync never
  writes repo files; gh# badges retired to display-only legacy; sync rides
  the agent's normal board push (an on-push Action mutating only GitHub-side
  cannot loop — it commits nothing); inline issue-create at intake, one
  best-effort call, `draft` label while the task is being written, cleared
  by the reconciler once the committed board carries it; worst case is a
  no-longer-needed issue closed as won't-fix — duplicates impossible.
- Platform facts settled in design: GITHUB_TOKEN pushes do not retrigger
  on:push workflows (callabloom app-token pushes DO — commits, if ever any,
  must use the default token); the ingest workflow is already sender-gated
  to the operator.
- Convergence property to test (the echo-loop lesson): push then ingest at
  fixed point must produce ZERO commits and ZERO issue mutations.

## Proposal

Rebuild the mirror leg on Decision-088:
1. board_gh matches tasks by id via the hidden field; the badge write-back
   code and `gh#` badge parsing as load-bearing state are removed.
2. A new on-push Action (paths: docs/**) runs the reconcile with
   GITHUB_TOKEN; it mutates GitHub components only, never commits.
3. Intake gains the inline create: one `gh issue create` (labels `board` +
   `draft`) + best-effort Project row when a sidecar/row is born.
4. The gardener's boot pull and post-write push calls retire; ingest stays
   as-is.

## Testing

- Fixed-point proof: full push, then pull, then the dispatched Action —
  zero ingested, zero commits, zero issue edits on the second pass.
- Inline-create proof: intake a scratch task → issue appears with `draft`;
  commit + push → reconciler clears `draft`; abandon path → close as
  won't-fix leaves board untouched.
