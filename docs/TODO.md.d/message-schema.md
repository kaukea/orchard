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

**Ruled, 2026-08-08 (operator, verbatim intent):** *"I'm going to tolerate
absolutely nothing... it's all new messages, all new formats, all new
enforcements, and I don't want to hear about compatibility at all anywhere
under any circumstance."* The previous attempts bought nothing worth
honouring: the schema is strict in BOTH directions — an off-schema message
is rejected on send and on read, no tolerance, no legacy fields, no
transition shims. `tools/message.schema.json` is the single schema
definition and evolves with the wire in the same commit (Decision-134
discipline).

## Testing

Bound by the parent's testing doctrine (`courier-messaging.md` §Testing, operator ruling 2026-08-08): unit tested to death, including the unit-test seam for an agent communicating with its counterparty; the scenario does not close without its tests written and run green.
