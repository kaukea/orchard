- created: 2026-08-08
- created_by: serialseb
- created_during: f/courier-messaging

# Read enforcing: a must-read that goes unread is pushed back

## Blockers

Needs the by-reference hand-up built first (`courier-messaging.md`,
scenario inbox-outbox/session-messaging).

## Questions

None open.

## Findings

- Precedent (operator, 2026-08-08): successfully done in OpenCode against an
  Opus that did not want to listen to instructions.

## Proposal

Operator, 2026-08-08: enforce that the agent actually reads a `must read`
file by looking at the LAST ACCESS TIME of the master agent's copy of the
file; if it has not been read, push the reference back into the agent's
prompt again until it reacts. Future task — not in the first build of the
hand-up.

## Testing

Bound by the parent's testing doctrine (`courier-messaging.md` §Testing, operator ruling 2026-08-08): unit tested to death, including the unit-test seam for an agent communicating with its counterparty; the scenario does not close without its tests written and run green.
