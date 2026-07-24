- created: 2026-07-24
- created_by: fable-5

## Blockers

- The bloomer must first be judged ready by the operator (Decision-073) —
  the groomer and every pipeline reference stay untouched until then.

## Questions

- What in the groomer definition is worth keeping (Decision-073's mandated
  analysis) — anything, or clean retirement?

## Findings

- Returned as follow-up #1 by the psychometric-discovery close (merged
  eaa8bae): repoint the orchestrator's §Blooming/handoff round and the
  `bloom-tasks` dispatch target from groomer to bloomer; the orchestrator
  adopts `tools/bloomer-launch.sh` / `bloomer-teardown.sh` (until then
  dispatch is manual/scripted).
- The wiring shape is ruled by Decision-075: the orchestrator dispatches the
  bloomer pane at intake and in the Decision-050 pre-launch slot, ANALYZES
  the statistical report itself, and owns the go/no-go — no
  delegate-and-forget.

## Proposal

(to shape when unblocked) Groomer analysis → keep/retire verdict; repoint
orchestrator definition and bloom-tasks skill to the bloomer; orchestrator
adopts the pane launch/teardown scripts; groomer definition retired per the
verdict.

## Testing

To agree when unblocked — expected: a full intake and a full pre-launch
round run through the bloomer pane with the orchestrator executing the
outcome; no reference to the groomer remains in the pipeline.
