- created: 2026-07-20
- created_by: Sebastien Lambla

## Blockers

- None — this is the gating work the rest of the programme waits on.

## Questions

- ~~Does [[architect-delegation]] fold into this contract rewrite or stay its own task?~~
  FOLDED IN (operator, 2026-07-20) — that entry is cancelled-as-absorbed; its content
  lives here now.
- ~~What is the completeness BAR for a build-ready sidecar?~~ RULED (Decision-025): the
  bar is the complete WHAT — definition, scope, constraints, scope answers; the HOW is
  the landscaper's own plan-phase output, never required at handoff. Landscaper discovers,
  plan-gated.
- ~~How are the operator's questions collected and asked?~~ RULED (Decision-025): two
  rounds — scope while parked, launch decisions at spawn; one scope round spans a
  cluster of RELATED features before any landscaper (cloud or local) launches.
- ~~(absorbed) What restores delegation trust?~~ RULED (Decision-025): sower dispatch
  mandatory above s-size, zero-sower builds fail the close gate; inline s-size builds
  are stated and justified in the close report.

## Findings

- Absorbed from [[architect-delegation]] (2026-07-20): the operator does not currently
  trust the landscaper — the 2026-07-20 role-dag build dispatched 4 Haiku explorers in
  discovery but built every step single-handed. The landscaper definition PERMITTED that
  ("directly or via parallel sowers"), so the contract, not just the behaviour, was
  the bug. Decision-023's deferred header-fill move re-evaluates when delegation trust
  is restored — the trigger lives here.
- Operator (2026-07-20): the lines between gardener and landscaper are VERY BLURRED.
  The split, now ruled: the GARDENER owns task relationships (priorities, relative
  importance, functional relevance) and the complete WHAT; the LANDSCAPER owns the HOW —
  discovery + technical design IS the role — then dispatches coders.
- Hard consequence: [[cloud-architect]] cannot work without this contract — a cloud
  agent cannot ping-pong questions mid-flight, so both rounds must be complete at
  dispatch. Delivered together, with strong gating (operator).

## Proposal

Encode the contract in the definitions — DONE 2026-07-20, directly on main
(gardener domain, Decision-065):

- `agents/architect.md`: sidecar = WHAT, HOW is the landscaper's; open scope question at
  launch = broken handoff (park, don't ask mid-build); sower dispatch mandatory above
  s-size, zero-sower builds fail the close gate; frontmatter description updated.
- `agents/gardener.md`: the WHAT-bar walked before every spawn; one scope round
  across related features before any launch; spawn carries only the launch round
  (model/effort scaling + parallel-launch offer).
- `AGENTS.files.md` §Sidecar: `## Proposal` redefined as the WHAT; the landscaper records
  the frozen plan there post-gate.
- `docs/decisions.md`: Decision-025.

## Testing

AGREED (operator, 2026-07-20): live-fire on the next landscaper launch, WITH BOTH
INTERACTIVE BOUNDARIES kept — the error rate is currently high enough that neither may
be skipped:

1. the question rounds are actually asked (scope while parked; launch round at spawn), AND
2. the plan is explicitly confirmed by the operator before MAKE IT SO.

Pass = the spawn was preceded by a walked WHAT-bar, no scope question reached the
operator mid-build, the plan gate fired, and the close report lists sower dispatches
(or the justified s-size inline note). The task stays open until that run passes.
