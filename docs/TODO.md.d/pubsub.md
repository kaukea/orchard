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
- NAME addressing exists on the branch: script-minted registry,
  nearest-first resolution, fan-out to every live holder.

## Proposal

Pub/sub as dictated 2026-08-08, and NAME addressing folded in from the
agent-to-agent scenario (operator, same day). Detail specified when reached.

## Testing

Bound by the parent's testing doctrine (`courier-messaging.md` §Testing, operator ruling 2026-08-08): unit tested to death, including the unit-test seam for an agent communicating with its counterparty; the scenario does not close without its tests written and run green.
