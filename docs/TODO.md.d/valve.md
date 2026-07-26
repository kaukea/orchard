- created: 2026-07-26
- created_by: Sebastien Lambla
- created_during: orchestrator session (post-bus-landing scope round)

## Findings

- OPERATOR RULING (2026-07-26): the side agent is called **Valve**, wearing
  the water-drop emoji (💧). It does NOT check finished work; it MONITORS
  the activity of a working agent in real time, ENFORCES decisions as they
  apply, and at each relevant phase gives a yes/no — a no FORCES REWORK at
  the moment of deviation, not at review. Two different agents by ruling:
  Valve is not the supervisor ([[close-family-fakes]]) — the supervisor
  routes flow and never judges; Valve judges and never routes.
- Composition over the bus: Valve's phase verdicts ride as outcome events
  the supervisor consumes at phase boundaries — a no becomes a rework loop
  in the flow. Valve enforces only RECORDED state (docs/decisions.md, the
  sidecar's WHAT); it invents no rules of its own.
- Relation to [[deviance-detection]] (gh#32, "surface drift when it
  happens, not weeks later"): Valve is that idea promoted from surfacing to
  gating — whether Valve absorbs or supersedes gh#32 is settled at Valve's
  design round.

## Proposal

Design round with the operator scheduled IMMEDIATELY AFTER the supervisor
design (operator, 2026-07-26). Scope, the phase vocabulary it gates on, the
enforcement corpus, and its board relations are defined there.

## Testing

Agreed at the design round.
