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
**Ruled, 2026-08-08 (operator) — the shutdown protocol:** the past race
condition where a courier could not go away because of its monitor must never
repeat. Shutdown is COMMUNICATED, never silent: the departing courier says —
through the status system — that it is shutting down and finishing work, and
declares ONCE a defined amount of time it needs; its owner agent knows of the
shutdown and waits on it for that declared duration. No courier disappears
without information. (Same shape as Decision-060: two closing messages, a
declared grace, then the owner acts.)

Agent advice on the handover mechanics (2026-08-08, awaiting any operator
correction): the inbox belongs to the SESSION, not the courier instance —
succession is monitor ownership changing hands, nothing is forwarded. An
outbox write is atomic and delivery is the dispatch's, so in-flight sends
need no waiting. The only stateful item is an outstanding blocking request:
the old courier keeps a watch narrowed by the script to exactly its awaited
replies, receives nothing else, hands them up, announces stopping/stopped
within its declared grace, and goes.

## Testing

Bound by the parent's testing doctrine (`courier-messaging.md` §Testing, operator ruling 2026-08-08): unit tested to death, including the unit-test seam for an agent communicating with its counterparty; the scenario does not close without its tests written and run green.
