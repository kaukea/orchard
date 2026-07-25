- created: 2026-07-25
- created_by: Sebastien Lambla
- created_during: f/bus-transport-v2

## Blockers

- ~~PARITY GATE (operator sequencing, 2026-07-25 morning).~~ DROPPED by
  operator ruling (2026-07-25 afternoon): "I think it's just killing it" —
  the old inbox-fed `sidebar_model.py` retires WITH the fan-out; no parity
  dance. Builds as part of [[bus-finishing]].

## Questions

- ~~Is parity now met?~~ MOOT — the parity gate is dropped (ruling above).

## Findings

- THE MONEY LEAK (operator, 2026-07-25): v1's fan-out announce — a courier telling
  every peer inbox "I'm a courier agent" wakes all agents, a large token cost. The
  sanctioned replacement is topic posts that subscribers filter, which
  [[bus-transport-v2]] shipped.
- `depart` fan-out is already safe to remove — nothing reads it.
- Tests that break on the cut: `test_bus.py` broadcast round-trip and the
  `test_bus_traffic` role tests; both need updating with the cut, not after.
- FULL BROADCASTS ARE FORBIDDEN (operator ruling): no broadcast to all — only
  posting to topics.

## Proposal

Replace v1's fan-out announce/broadcast in `bus.py` with topic posts via
`orchard_topic.py` (plus unicast-to-parent where a directed message is the
point), remove the dead `depart` fan-out, and update the affected tests —
killing the token leak. Aggressive cut-over once the parity gate opens: land
the change and rip out the fan-out together, live at merge + kauk sync.

## Testing

- `test_bus.py` / `test_bus_traffic` updated and green with the fan-out gone.
- Live check on the operator's screen: the sidebar still shows identity and
  status for a running session after the cut (nothing went blind).
