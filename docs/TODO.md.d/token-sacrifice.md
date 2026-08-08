- created: 2026-08-08
- created_by: serialseb
- created_during: f/courier-messaging

# Token sacrifice

## Blockers

None.

## Questions

None open — content deliberately deferred to the scenario's turn.

## Findings

(none yet)

## Proposal

**Ruled, 2026-08-08 (operator):** the courier is functionally a stateless
translator — the script does the work; it needs a tiny, constant context and
none of the base context — yet its transcript grows with every wake. The
feature: at a MAXIMUM TOKEN COUNT the courier requests its parent to spawn a
new courier; as soon as the new one is spawned, the old one goes away. The
ADDITION over the earlier idea (bus-recycling, gh#213 — same mechanics,
written twice because good ideas come many times over): the old courier must
FINISH its in-flight work — a dispatch, a blocking request/response — before
going, while new messages are denied to it / taken by the new courier.
Handover technicalities open; agent advice invited (recorded in Findings
once the operator has ruled on it).

## Testing

Bound by the parent's testing doctrine (`courier-messaging.md` §Testing, operator ruling 2026-08-08): unit tested to death, including the unit-test seam for an agent communicating with its counterparty; the scenario does not close without its tests written and run green.
