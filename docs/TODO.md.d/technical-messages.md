- created: 2026-08-08
- created_by: serialseb
- created_during: f/courier-messaging

# Pure technical messages handled directly by the monitor

## Blockers

None.

## Questions

None open.

## Findings

- Direction consistent with the archived spec §6: the script/monitor layer is
  free; waking an agent is the only real cost. A technical message the
  monitor can answer or absorb must never reach the agent.

## Proposal

**Ruled, 2026-08-08 (operator):** purely technical messages are the ones
that do not require the agent to be talked to — the script receives and
responds immediately without ever breaching the AI boundary. Two examples
are already documented in the branch spec and are not restated here:
IDENTITY and STATUS (`docs/courier-wire.md` §2b under `archive/observability`
— answered inside the script, zero tokens, Decision-130). The same class:
uptime, request counts, ping-pong — script to script, so it is free.

## Testing

Bound by the parent's testing doctrine (`courier-messaging.md` §Testing, operator ruling 2026-08-08): unit tested to death, including the unit-test seam for an agent communicating with its counterparty; the scenario does not close without its tests written and run green.
