- created: 2026-08-08
- created_by: serialseb
- created_during: f/courier-messaging

# Tree messaging: inherited parent identity, names resolved within the tree

## Blockers

None.

## Questions

None open.

## Findings

- Today's mechanism: parent identity passed at launch via environment
  (`ORCHID_PARENT_SESSION`), site by site — the operator calls this dance
  brittle, and the archived branch had already deleted the directed
  parent-callback (`cmd_signal`) in favour of events.

## Proposal

Operator, dictated 2026-08-08 (reading marked where transcription wobbled):
each agent INHERITS from its parent agent and always knows its parent's ROLE
and SESSION ID as a structural property — not something passed hop by hop at
launch [reading: replaces the current passing of parent identity to each
launched agent, which is brittle]. If a use is found, sending a message by
name then resolves against only the names relevant to YOUR tree.

## Testing

Bound by the parent's testing doctrine (`courier-messaging.md` §Testing, operator ruling 2026-08-08): unit tested to death, including the unit-test seam for an agent communicating with its counterparty; the scenario does not close without its tests written and run green.
