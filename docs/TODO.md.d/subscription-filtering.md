- created: 2026-08-08
- created_by: serialseb
- created_during: f/courier-messaging

# Subscription filtering: filter messages when subscribing to pub/sub

## Blockers

Needs the pub/sub scenario built first (`pubsub.md`).

## Questions

None open.

## Findings

(none yet)

## Proposal

Operator, 2026-08-08: a REQUIRED task before project-level broadcast — enable
message filtering when subscribing to pub/sub, so a subscriber receives only
what it cares about from a topic. Detail specified when reached.

## Testing

Bound by the parent's testing doctrine (`courier-messaging.md` §Testing, operator ruling 2026-08-08): unit tested to death, including the unit-test seam for an agent communicating with its counterparty; the scenario does not close without its tests written and run green.
