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

Scenario as dictated 2026-08-08: purely technical messages are handled
directly by the monitor, never waking the agent. Detail specified when
reached.

## Testing

Bound by the parent's testing doctrine (`courier-messaging.md` §Testing, operator ruling 2026-08-08): unit tested to death, including the unit-test seam for an agent communicating with its counterparty; the scenario does not close without its tests written and run green.
