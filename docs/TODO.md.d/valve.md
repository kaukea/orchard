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

DICTATED CHARTER (operator, 2026-07-26 design round):

- Valve's role: ensure and enforce rules such as — tasks following their
  ORIGINAL INTENT; features NOT being created that were not specified; the
  GOAL of the work being respected by the coding agent.
- Valve comes with ITS OWN CONTEXT — it knows what to look for,
  independently of the worker it watches.
- The yes/no fires AT THE END of an agent's piece of work (refines the
  earlier "at each relevant phase" phrasing: the gate is the work-unit
  boundary, not a mid-work interrupt). A no forces the agent into a RETRY —
  one second attempt.
- RULED: on the second attempt, if Valve is still not confident with the
  code, the TASK FAILS — the pipeline stops and the failure surfaces to the
  operator with Valve's reasons; no third try without the operator's say.

Still open (this design round, in progress): who assembles Valve's context;
verdict mechanics on the bus; confidence criteria; whether Valve absorbs
[[deviance-detection]] (gh#32).

## Testing

Agreed at the design round.
