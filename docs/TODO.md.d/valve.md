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
  routes flow and never checks; Valve checks and never routes.
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

RULINGS (operator, 2026-07-26, continued):

- CONTEXT: Valve reads durable state ITSELF (sidecar WHAT, decisions,
  original intent) — nobody curates for it, so nobody can curate away from
  it. The supervisor hands no digest.
- ADVICE: Valve CAN also advise — alternative approaches drawn from the
  project's ethos, offered at the relevant moment alongside the verdict.
- WHEN IT RUNS — the two-tier ladder, ephemeral both tiers, NEVER resident
  (operator constraint: no paying for a continuously-running side agent):
  - Per COMMIT, the light pass: diff vs the sidecar's intent — does the
    change belong to the spec, any unasked-for feature. Small context,
    cheap; catches drift at the moment it happens.
  - Per PIECE-OF-WORK END, the full gate: the ruled yes/no over the whole
    work product vs intent/goal/decisions, with the retry semantics
    (no → one retry → second no → task fails to the operator with reasons).
- STATELESS: the sidecar WHAT + the diff ARE the ledger; the only
  cross-invocation memory the flow needs (attempt count) is routing data
  and lives with the supervisor. Research anchor: the Microsoft
  ledger-orchestration discussions (task ledger / progress ledger — the
  held "ledger v0" item); Valve is that idea made ephemeral.

- gh#32 FATE: decided AT VALVE'S BUILD (operator, 2026-07-26) —
  [[deviance-detection]] stays untouched until Valve exists and its
  coverage is observable.
- MODEL: cheap by design — HAIKU is probably the one we go for (operator,
  2026-07-26, side note). Direction, pinned at build; whether the full
  end-of-piece gate warrants a higher tier than the per-commit pass is
  checked at build (this note mine, not a ruling).

## Voluntary deferrals (explicit, not blockers)

- CONFIDENCE CRITERIA for the full gate (operator, 2026-07-26): deferred to
  the build's plan gate — the build presents concrete criteria (intent
  match, no unspecified features, goal respected, honest tests) for
  operator approval before coding.
- gh#32 absorption: decided at build (ruling above).
- Model pin: Haiku direction confirmed at build (ruling above).

Design round CLOSED 2026-07-26 — the WHAT is complete; readiness projected
plan-ready.

## Testing

Method agreed at the plan gate together with the confidence criteria (the
deferral above); known acceptance shape — a live piece of work checked by an
ephemeral Valve: a compliant change passes, a planted out-of-spec change
draws a no with reasons and forces the retry, a second no fails the task
to the operator.
