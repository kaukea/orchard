- created: 2026-08-08
- created_by: serialseb
- created_during: f/courier-messaging

# Subscription filtering: filter messages when subscribing to pub/sub

## Blockers

Needs the pub/sub scenario built first (`pubsub.md`).

## Questions

None open.

## Findings

(none yet)

## Proposal

Operator, 2026-08-08: a REQUIRED task before project-level broadcast.

**Ruled, 2026-08-08 (operator):**

- Filtering is RECEIVER-SIDE: making the dispatch read every recipient's
  filters before delivering is too complex for a human to maintain. Copies
  into inboxes are literally free (only directed messages need be a single
  copy), so the courier's simplified script filters locally — discarding
  what is not addressed to it (the WHO).
- The WHAT is SUBJECT-ONLY: an include list, or an exclude list
  (everything-except, expected rare), over message types.
- `*` PREFIX MATCHING on subjects is kept — with `*` enforced as a RESERVED
  character when publishing.
- JSON body filtering is per-schema, per-message — DEFERRED, except for the
  common fields always present in the body: STATUS and the information
  (identity) fields — enabling filters on e.g. agent types. That covers
  ninety-nine percent; the complexity waits for later.

## Testing

Bound by the parent's testing doctrine (`courier-messaging.md` §Testing, operator ruling 2026-08-08): unit tested to death, including the unit-test seam for an agent communicating with its counterparty; the scenario does not close without its tests written and run green.
