- created: 2026-08-08
- created_by: serialseb
- created_during: f/courier-messaging

# Fixed schema for messages, no exception

## Blockers

None.

## Questions

None open.

## Findings

- `tools/message.schema.json` exists on main and branch; the branch validates
  strict-on-write, tolerant-on-read for retired fields, subjects always
  strict.

## Proposal

Scenario as dictated 2026-08-08: a fixed schema for messages, no exception.
Detail specified when reached.

## Testing

Bound by the parent's testing doctrine (`courier-messaging.md` §Testing, operator ruling 2026-08-08): unit tested to death, including the unit-test seam for an agent communicating with its counterparty; the scenario does not close without its tests written and run green.
