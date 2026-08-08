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

**Ruled, 2026-08-08 (operator):** an agent can send a message to its parent —
and to ANY agent on its PATH TO THE ROOT (the root today is the
orchestrator, where parent-addressing is of little use). Ancestor addressing
is a first-class address form resolved from the inherited linkage; the agent
never handles a session id to reach an ancestor. Siblings, subtrees and any
other lateral messaging: NO decision taken — out of scope, parked, never to
be assumed by an implementer.

**Clarified, 2026-08-08 (operator):** the name in this task is the AGENT
name. Sending by agent name, resolved against only the names in your own
tree, belongs HERE. The pub/sub scenario's names are TOPIC names — nothing
to do with these. The branch's name-registry code is this task's reference
material.

## Testing

Bound by the parent's testing doctrine (`courier-messaging.md` §Testing, operator ruling 2026-08-08): unit tested to death, including the unit-test seam for an agent communicating with its counterparty; the scenario does not close without its tests written and run green.
