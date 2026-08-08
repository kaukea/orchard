- created: 2026-08-08
- created_by: serialseb
- created_during: f/courier-messaging

# Documentation for other components: decoupling through events

## Blockers

None.

## Questions

None open.

## Findings

- The archived wire spec §7 already states the event rules (state is read,
  never inferred; two-event ending; creator-closes). This scenario writes the
  documentation OTHER components consume to integrate through events.

## Proposal

Scenario as dictated 2026-08-08: documentation for other components to
understand decoupling through events. Detail specified when reached.

## Testing

Bound by the parent's testing doctrine (`courier-messaging.md` §Testing, operator ruling 2026-08-08): unit tested to death, including the unit-test seam for an agent communicating with its counterparty; the scenario does not close without its tests written and run green.
