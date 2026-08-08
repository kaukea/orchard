- created: 2026-08-08
- created_by: serialseb
- created_during: f/courier-messaging

# Pub/sub, including NAME addressing

## Blockers

None.

## Questions

None open.

## Findings

- The archived branch implements the layer main lacks: `subscribe` creates
  `orchard/topics/<name>/<sid>/`, publish fans copies into currently
  subscribed folders only, monitor adds only subscribed folders as watch
  sources (`93f44f5` and surroundings). The 2026-08-08 courier self-wake on
  main is the absence of this layer.
- The branch's NAME-addressing code (script-minted registry, nearest-first
  resolution, fan-out to every live holder) is AGENT-name machinery — reference
  material for `tree-messaging.md`, not for this task.

## Proposal

Pub/sub as dictated 2026-08-08. **Clarified by the operator, 2026-08-08: the
NAME here is the TOPIC name** — agent-name addressing is a different name
entirely and lives in `tree-messaging.md`; the two have nothing to do with
one another. Detail specified when reached.

## Testing

Bound by the parent's testing doctrine (`courier-messaging.md` §Testing, operator ruling 2026-08-08): unit tested to death, including the unit-test seam for an agent communicating with its counterparty; the scenario does not close without its tests written and run green.
