# Bus recycling: a deep courier warns its host and hands over to a fresh one

- created: 2026-07-22
- created_by: Sebastien Lambla

## Blockers

- None hard; builds on the one-per-agent invariant of [[bus-singleton]]
  (the handover must never leave two live couriers beyond the crossover
  instant).

## Questions

- How the courier measures its own depth (the harness does not expose token
  counts to the agent): wake-count proxy, transcript-size stat, or a
  host-side counter — the build picks and states the mechanism.
- Threshold value to warn at (operator sized it only as "a small number").

## Findings

- Operator intake (2026-07-22, nice-to-have): long-lived courier sidecars
  accumulate resident context — the 2026-07-22 gardener courier grew from
  ~23k to ~53k tokens across 44 wakes, each late wake replaying the whole
  transcript to emit one line — when the role is forwarding file-backed
  messages. Rotation is cheap BECAUSE the state is on disk: nothing to
  transfer.

## Proposal

When a courier sidecar nears its depth threshold it sends its host a warning
("this is suicide" — its own retirement notice); the host spins a fresh courier
sidecar and tells the old one it can go; the old courier departs cleanly
(Decision-041 release choreography, Decision-051 invariant preserved —
exactly one live courier per agent outside the crossover instant). Adjacent
economy noted, not in scope: the more courier duties become pure script (the
broadcast and popup paths already did), the less model context a courier needs
at all.

## Testing

Drive a courier past the threshold with synthetic traffic: the warning arrives
at the host, the replacement announces, the old departs, no message in the
crossover window is lost (disk-backed inbox drained by the successor), and
the sidebar shows one courier row throughout.
