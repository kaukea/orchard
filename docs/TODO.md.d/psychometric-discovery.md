- created: 2026-07-20
- created_by: Sebastien Lambla

## Blockers

- None; builds on the scope round the handover contract defines ([[handover-contract]],
  Decision-025).

## Questions

- ~~Which measurement techniques transfer: adaptive questioning (next question = the one
  that most reduces uncertainty about the intended feature, CAT-style), multi-item
  triangulation (several small probes instead of one broad "what do you want"),
  consistency checks across answers (flag contradictions as a reliability signal),
  forced-choice items to separate near-alternatives?~~ Resolved by the 2026-07-24
  blueprint: all of them — EIG-driven adaptive selection, funnel broad→narrow,
  forced-choice items, cross-answer consistency (person-fit) checks.
- ~~What is the convergence criterion — when is the WHAT "measured" well enough to pass
  the WHAT-bar and stop asking?~~ Resolved: an explicit convergence number from the
  statistical engine (uncertainty / standard-error-threshold stop), reported with the
  result.
- ~~What triggers the instrument: operator says "fuzzy", or the orchestrator detects it
  (vague nouns, no testable outcome, conflicting constraints)?~~ Resolved: it runs at
  intake (feature birth) and in the Decision-050 pre-launch slot, dispatched by the
  orchestrator; continuous-convergence triggering comes later with the notify channel.
- ~~Where does it live: orchestrator definition, a dedicated skill the scope round loads,
  or prompts inside the readiness pipeline?~~ Resolved: a dedicated agent under the
  `bloomer` name plus a statistical engine script; it interacts from its own pane inside
  the orchestrator's window.

## Findings

- Operator suggestion (2026-07-20): apply psychometric test measurement logic to feature
  discovery when a feature seems fuzzy or not well defined. Context: the scope round
  (Decision-025) is where the WHAT gets defined; for fuzzy features a structured
  instrument beats free-form questioning — the same problem psychometrics solves for
  latent constructs (the intended feature is the latent variable; scope questions are
  the items).
- PROMOTED to the bloomer's standard charter (Decision-027): the bloomer closes the
  functionality scope with targeted questions on functional completeness, leaves loose
  ends as explicit voluntary deferrals, and decides by a statistical-probability
  criterion that the scope is well enough defined — then kicks the architect off
  automatically. The convergence criterion IS this task's subject; it is no longer only
  a fuzzy-feature special case. Names land via [[retire-groom-vocabulary]].

- Operator charter sharpened (2026-07-24): blooming operates at the FUNCTIONALITY
  DEFINITION level — turning a two-to-three-sentence functional spec into a complete
  understanding of what the operator wants — which is explicitly NOT the orchestrator's
  job (the orchestrator does relationships, board placement, delivery). Target
  interaction shape: the operator spends one morning hour with the instrument, then
  everything else runs without him. The existing clerk implementation was demoted to
  the `groomer` name (deliberately forbidden vocabulary, as a not-to-persist marker);
  this task's instrument is to be rebuilt separately and takes the `bloomer` name.
  Design inputs: the 2026-07-24 blueprint (EIG/BED question selection, corpus priors,
  convergence-triggered launch; orchestrator workstream log) and the
  [[bloomer-forensics]] investigation into how the divergence happened.

- Scope round closed (operator, 2026-07-24, orchestrator session): graduated
  convergence outcome (see Proposal); interaction in its own pane inside the
  orchestrator window, 3/4 height, orchestrator holding 1/4 awaiting results;
  corpus priors deferred (corpus-indexing still running) behind an explicit stub
  interface; live test = [[writing-emails]] gh#15; launch tier claude-fable-5 ·
  xhigh. Operator ruling recorded for later: once the statistical composition is
  ready, per-role model/effort DEFAULTS are removed altogether — launch sizing
  becomes measured, not pinned.
- Cloud surface scoped out of v1: GitHub has no iterative-survey primitive —
  comment rounds and checkbox task-lists only, a degraded shape (operator asked,
  confirmed 2026-07-24).

## Proposal

V1 of the rebuilt bloomer — the Decision-027 intake measurement instrument, built
from scratch under the `bloomer` name. The demoted `groomer` clerk is NOT a
starting point: when this lands, the clerk's definition is deleted and every
pipeline reference (the orchestrator's Decision-050 bloom round, the
`bloom-tasks` skill) points at the rebuilt agent.

In scope (v1):

- A dedicated `bloomer` agent that turns a two-to-three-sentence functional spec
  into a converged WHAT: adaptive questioning where the next question is the one
  that most reduces uncertainty about the intended feature, funnel-structured
  broad→narrow, forced-choice items to separate near-alternatives, and
  cross-answer consistency checks as a reliability signal.
- Question selection and stopping owned by a STATISTICAL ENGINE (a script);
  phrasing and parsing owned by the LLM. The engine emits an explicit
  convergence number (uncertainty / SE-threshold stop) that is written into the
  task's sidecar with the result.
- Graduated outcome at convergence (operator, 2026-07-24): very-high confidence
  → auto-kick the architect; medium-high → ask the operator to confirm the
  launch; anything lower → return to the orchestrator for replanning. The
  auto-kick special case is explicitly TEMPORARY — it is removed and delegated
  once the autonomy ladder/metronome lands.
- Interaction surface: the instrument runs interactively in its OWN PANE inside
  the orchestrator's window — 3/4 height, the orchestrator keeping 1/4 and
  awaiting results — asking through the built single/multiple-choice question
  machinery.
- Underspecification detection: asking is gated on measured low confidence,
  never on a fixed question count; loose ends close as explicit voluntary
  deferrals (Decision-027) recorded in the task's sidecar.
- Corpus priors DEFERRED: the prior interface ships as an explicit stub; v1 asks
  without corpus-informed priors.

Out of scope (v1): corpus-derived priors; the autonomy ladder and metronome
integration; the cloud/issue-comment surface (no iterative-survey primitive on
GitHub); statistical launch sizing (future ruling above).

Design inputs (the HOW stays the architect's; these are references, not orders):
blueprint §8 of the 2026-07-24 operator-knowledge whiteboard — engine/LLM split
(OPEN, arXiv:2403.05534), EIG/BED question selection (arXiv:2508.21184), funnel
structure (arXiv:2510.12015), CAT/IRT Fisher-information selection with
SE-threshold stopping (arXiv:2511.04689, arXiv:2508.07279), underspecification
detection (arXiv:2502.13069, ClarifyGPT, arXiv:2406.00922), person-fit
consistency checks.

## Testing

Agreed (operator, 2026-07-24): a live run — take [[writing-emails]] (gh#15,
boarded as "scope to be defined by the operator", the purest fuzzy case) through
the instrument. Pass = the run produces a converged WHAT with its convergence
number, the operator judges the resulting sidecar passes the WHAT-bar, and the
graduated outcome fires per its confidence band (on a first calibration run the
expected band is ask-to-confirm, not silent auto-kick).
