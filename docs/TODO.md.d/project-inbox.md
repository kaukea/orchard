- created: 2026-08-08
- created_by: serialseb
- created_during: f/courier-messaging

# Project inbox

## Blockers

None.

## Questions

None open.

## Findings

(none yet)

## Proposal

Added by the operator, 2026-08-08: "We also need a task for project inbox."
An inbox at PROJECT scope, alongside the per-courier inbox of inbox-outbox.
Detail specified when the scenario is reached; its position in the build
order is not yet assigned.

## Testing

Bound by the parent's testing doctrine (`courier-messaging.md` §Testing, operator ruling 2026-08-08): unit tested to death, including the unit-test seam for an agent communicating with its counterparty; the scenario does not close without its tests written and run green.
