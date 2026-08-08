- created: 2026-08-08
- created_by: serialseb
- created_during: f/courier-messaging

# Project-level broadcast

## Blockers

None.

## Questions

None open.

## Findings

- The branch spec rules out broadcast-to-everyone; project scope is the
  existing project-topic feed. What "broadcast" means at project level is
  specified when this scenario is reached.

## Proposal

Scenario as dictated 2026-08-08: project-level broadcast. Detail arrives when
the scenario is reached, per the one-at-a-time method.

## Testing

Bound by the parent's testing doctrine (`courier-messaging.md` §Testing, operator ruling 2026-08-08): unit tested to death, including the unit-test seam for an agent communicating with its counterparty; the scenario does not close without its tests written and run green.
