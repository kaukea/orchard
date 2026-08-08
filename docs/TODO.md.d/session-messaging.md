- created: 2026-08-08
- created_by: serialseb
- created_during: f/courier-messaging

# Agent-to-agent: session-based directed messaging only

## Blockers

Ordering (operator, 2026-08-08): inbox-outbox is built first.

## Questions

None open.

## Findings

- Four-corner comparison done 2026-08-08 (see parent sidecar): branch deletes
  `signal`/`notify_user`/`operator_origin` (main still carries all three, and
  `signal`'s prefix handling is proven buggy); branch adds strict-on-write,
  tolerant-on-read for retired envelope fields; branch suites include the
  real-CLI seam pattern.

## Proposal

Scoped by the operator, 2026-08-08: session-based directed messaging ONLY —
send/request/reply over `:session:` addresses. NAME addressing is folded into
the pubsub scenario; priorities are not in this scenario.

## Testing

Bound by the parent's testing doctrine (`courier-messaging.md` §Testing, operator ruling 2026-08-08): unit tested to death, including the unit-test seam for an agent communicating with its counterparty; the scenario does not close without its tests written and run green.
