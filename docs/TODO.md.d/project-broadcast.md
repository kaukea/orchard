- created: 2026-08-08
- created_by: serialseb
- created_during: f/courier-messaging

# Project-level broadcast

## Blockers

None.

## Questions

None open.

## Findings

- The old project-wide broadcast caused the parallel-worktree bugs; main's
  spec records the one-project-dir-per-worktree fix as landed 2026-07-27
  (docs/orchard-bus.md §4 [CODE, fixed]) — verified in the document, not
  re-tested.

## Proposal

**Ruled, 2026-08-08 (operator):** just as an ask is just a request/response
with a format, project-level broadcast IS project-level pub/sub — no separate
mechanism. The project topic is CREATED when the project is opened and CLOSED
when the project is closed. Its purpose, by example: telemetry, diagnostics,
cleanup on an early shutdown — the occasions being agent starting, agent
finishing, agent failing. REQUIRED before this task: subscription-time
message filtering (`subscription-filtering.md`).

## Testing

Bound by the parent's testing doctrine (`courier-messaging.md` §Testing, operator ruling 2026-08-08): unit tested to death, including the unit-test seam for an agent communicating with its counterparty; the scenario does not close without its tests written and run green.
