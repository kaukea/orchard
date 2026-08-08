- created: 2026-08-08
- created_by: serialseb
- created_during: f/courier-messaging

# Fixed list of subjects any agent may send, no exception

## Blockers

None.

## Questions

None open.

## Findings

- The closed subject vocabulary exists in both specs
  (`ORCHARD_VALID_SUBJECTS`); the branch spec flags the `bus` literals
  (Decision-131 name retirement) as awaiting the operator's word since he
  dictated those exact strings.

## Proposal

Scenario as dictated 2026-08-08: a fixed list of subjects able to be sent by
any agent, no exception. Detail specified when reached.

## Testing

Bound by the parent's testing doctrine (`courier-messaging.md` §Testing, operator ruling 2026-08-08): unit tested to death, including the unit-test seam for an agent communicating with its counterparty; the scenario does not close without its tests written and run green.
