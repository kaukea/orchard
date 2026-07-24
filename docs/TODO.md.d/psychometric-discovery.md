- created: 2026-07-20
- created_by: Sebastien Lambla
- completed: 2026-07-24
- completed_during: f/psychometric-discovery

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

- LIVE TEST (2026-07-24 14:0x, verified by observation): full round on
  [[writing-emails]] (gh#15) through the bloomer pane, launched from this
  worktree via `tools/bloomer-launch.sh`. Overall SE 0.461 → band "lower" →
  task returned for replanning, no launch — the correct graduated outcome for
  a first calibration run. 3/5 dimensions converged; one consistency check
  fired and resolved to a rule; a launch-sizing recommendation was emitted
  (l · fable-5 · high), not executed. The bloom commit (80f74d8) rides this
  branch; pane teardown verified clean (return pane restored, `.return-pane`
  removed, board lint 0 errors).
- v1 CALIBRATION LIMITATION (measured in the live run): the ordinal-index
  entropy SE proxy has a floor for multi-select/subset answers — both
  multi-select dimensions EXHAUSTED their item budgets instead of converging
  despite consistent answers (email-domain plateaued SE 0.901→0.888 over four
  rounds), so the overall band is dragged to "lower" by construction whenever
  multi-select dimensions dominate. Follow-up candidate: a subset-posterior
  model for multi-select dimensions.

Result: **done** · branch `f/psychometric-discovery` (🎉 anchor `045f16f`,
`Base: 867d5e1`; implementation through `80f74d8`, close-out docs commit on
top) · tested per `## Testing`: the agreed live run on writing-emails was
executed and passed — a converged WHAT with its explicit convergence number
written into the task's sidecar, and the graduated outcome fired per its
confidence band (lower → returned for replanning, no launch). Fan-out:
discovery 7 explorers; build 3 builders + 2 steps inline (sidecar staging in
the architect's own words; a 3-symlink wiring); close-out docs staged inline
by the successor session after a tmux crash killed the predecessor
post-test. ARCHITECTURE: updated in-branch — the bloomer role-table row
rewritten for the rebuilt instrument (component-repurposed trigger) and the
cloud-surface blooming clause aligned with the v1 cloud deferral. MIGRATION:
none — no managed artifact was moved, renamed, or reformatted (the
predecessor prep definition is untouched; every shipped file is new).

Follow-ups returned to the orchestrator (board placement is the
orchestrator's, never written here):

1. Predecessor-clerk analysis/retirement and the pipeline repoints
   (orchestrator §Blooming/handoff round, `bloom-tasks` dispatch target)
   once the bloomer is judged ready — operator ruling, staged as a Decision
   entry below.
2. Multi-select SE floor: a subset-posterior model for multi-select
   dimensions, so consistent subset answers can converge instead of
   exhausting (calibration limitation above).
3. [[writing-emails]] came back at band "lower" and needs orchestrator
   replanning; its bloomed sidecar and board move ride this branch
   (80f74d8).

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

### Frozen plan (architect, 2026-07-24, MAKE IT SO after two amendment rounds)

Components, landing ALONGSIDE the untouched `groomer` (no deletion, no
repoints in this branch — operator ruling at the plan gate):

- `agents/bloomer.md` — claude-fable-5 · xhigh; the charter implemented IN the
  definition (bloomer-forensics guardrail), serving pass mode and the
  Decision-050 handoff round; single-writer on its task's sidecar; asks via
  native single/multiple-choice prompts in its own pane.
- `tools/bloom_engine.py` — stdlib-only python3; owns selection and stopping:
  blueprint-§8 composition in full — EIG/BED question selection over the
  latent feature hypothesis space PLUS IRT item modelling with
  Fisher-information selection and SE-threshold stopping (operator override
  of the Opus-review drop; item parameters LLM-assumed, flagged uncalibrated
  in the report), funnel broad→narrow, forced-choice item support, person-fit
  consistency checks. Emits the explicit convergence number, the graduated
  band, and a Decision-019 launch-sizing recommendation.
- Priors stub: engine-level interface defaulting to uninformative priors; its
  contract documents the future corpus feed — all repos under ~/src/serialseb
  and ~/src/SafeKeepIt are recent agentic work and form the corpus (operator,
  2026-07-24).
- Pane surface: launch + teardown scripts in `tools/` — bloomer pane split
  inside the orchestrator's window (3/4 height, orchestrator keeps 1/4),
  ORCHID_PARENT_SESSION wired for direct bus signalling, focus returned on
  teardown. The orchestrator adopts these at the deferred repoint; until
  then dispatch is manual/scripted.

Graduated outcome mechanics: the bloomer REPORTS its band over the bus; the
ORCHESTRATOR executes any launch (very-high band auto-launch stays TEMPORARY,
removed when the autonomy ladder/metronome lands).

Additional deferral (operator, plan gate): groomer analysis/retirement and
the orchestrator + `bloom-tasks` repoints happen in a follow-up after the
bloomer is judged ready — not in this branch.

## Testing

Agreed (operator, 2026-07-24): a live run — take [[writing-emails]] (gh#15,
boarded as "scope to be defined by the operator", the purest fuzzy case) through
the instrument. Pass = the run produces a converged WHAT with its convergence
number, the operator judges the resulting sidecar passes the WHAT-bar, and the
graduated outcome fires per its confidence band (on a first calibration run the
expected band is ask-to-confirm, not silent auto-kick).

## Operator requests

- 2026-07-24 12:28 (mid-discovery): "you are missing the discussion from last
  night; all repos under serialseb and SafeKeepIt are recent agentic work" —
  IMPLEMENTED: 20260724-session.md + both blueprint reviews folded into the
  plan; the corpus fact is recorded in the priors-stub contract.
- 2026-07-24 plan gate: include IRT/Fisher machinery in the v1 engine —
  IMPLEMENTED in the frozen plan.
- 2026-07-24 plan gate: leave `groomer` untouched under its name until the
  bloomer is ready, then analyze what is worth keeping — IMPLEMENTED as an
  explicit deferral; follow-up returned to the orchestrator at close.
- 2026-07-24 plan gate: launch sizing is already part of the pipeline
  (Decision-019); dropping it would be a regression — IMPLEMENTED: the
  convergence report carries a launch-sizing recommendation.

## Changelog entry

Bloomer v1 — the rebuilt intake-measurement instrument (charter:
Decision-027), landing alongside the untouched groomer.

- `tools/bloom_engine.py` is the statistical engine behind the bloomer
  intake-measurement agent: a stdlib-only Python 3 CLI
  (`init`/`next`/`answer`/`report`/`selftest`) that holds a discrete
  posterior per scope dimension, selects the next probe by
  expected-information-gain composed with an IRT/Fisher-information layer
  over LLM-assumed 2PL item parameters, enforces a broad-before-narrow
  funnel, and stops each dimension once its posterior standard error crosses
  a threshold or its item budget runs out. It flags contradictory answers
  via an lz-like person-fit statistic, reports a graduated
  very-high/medium-high/lower confidence band, and recommends a launch size
  (s/m/l) mapped to the current per-role model/effort tiers
  (Decision-018/019). Every report unconditionally flags its IRT parameters
  as uncalibrated, per operator ruling, since v1 ships with LLM-guessed
  rather than corpus-derived item statistics; `init --priors` accepts a
  per-dimension hypothesis-weight JSON file today as a stub for the intended
  future corpus-derived prior feed.
- The bloomer agent (`agents/bloomer.md`) is rebuilt from scratch as the
  Decision-027 intake-measurement instrument, replacing the demoted `groomer`
  clerk that only cited its charter without implementing it — every charter
  behaviour (adaptive dimension decomposition, engine-driven question
  selection and SE-threshold stopping via `bloom_engine.py`, native
  forced-choice prompts, misfit consistency checks, graduated launch outcomes
  by confidence band) is now a concrete procedure in the definition body. It
  runs in its own pane inside the orchestrator's window, gates every question
  on the statistical engine's measured-low-confidence verdict rather than a
  fixed count, and writes its converged WHAT — with an explicit
  uncalibrated-items caveat, since v1's IRT item parameters are LLM-assumed
  rather than corpus-calibrated — back into the task's sidecar. The existing
  `groomer.md` was left untouched, per operator ruling, pending a separate
  future retirement decision.
- `tools/bloomer-launch.sh` and `tools/bloomer-teardown.sh` give the bloomer
  its own tmux pane inside the orchestrator's existing window instead of a
  whole window: launch splits the current window with the bloomer taking the
  bottom 75% of height and the orchestrator's calling pane kept visible in
  the top 25%, recording a `.return-pane` (pane id + socket) under
  `.git/the-works/<task-id>/`; teardown, run by the bloomer as its last act,
  reads that file, refuses to ever kill the return pane, and hands focus
  back before closing its own pane. This is the pane-scoped counterpart to
  the architect's window-scoped `architect-teardown.sh`, reusing its
  socket-aware `tx()` wrapper and `%N`-pane-id return contract.

## Readme delta

Replace the bloomer paragraph in "Five agents, one assembly line" ("While
you think, the **bloomer** keeps the backlog sharp …") with:

> While you think, the **bloomer** measures what you actually want: point it
> at a fuzzy task and it asks the fewest questions that most reduce
> uncertainty — chosen by a statistical engine, not by feel — until the
> scope converges with an explicit confidence number. High confidence can
> launch the work; anything less comes back to you with the loose ends
> named.

(Ingest note, not README text: scheduled backlog-prep passes still run under
the demoted predecessor definition until the repoint follow-up; the README
describes the bloomer role as shipped.)

## Decision entries

## [2026-07-24 13:05 CEST] Decision-NNN: Bloomer v1 engine includes IRT/Fisher despite uncalibrated items
#bloomer #psychometrics #irt #eig #engine #convergence

Operator ruling (2026-07-24, plan gate): the v1 statistical engine implements
the full blueprint-§8 composition — EIG/BED question selection AND IRT item
modelling with Fisher-information selection and SE-threshold stopping —
overriding the Opus blueprint review's recommendation to drop the IRT/Fisher
formalism at n=1. Mitigation recorded with the ruling: item parameters are
LLM-assumed at generation and every convergence report flags them as
uncalibrated; accumulated live runs are the future calibration path.

## [2026-07-24 13:05 CEST] Decision-NNN: Groomer stays under its name until the bloomer is judged ready
#bloomer #groomer #retirement #pipeline #bloom-tasks

Operator ruling (2026-07-24, plan gate): the demoted `groomer` definition and
every pipeline reference to it (orchestrator bloom round, `bloom-tasks` skill)
stay UNTOUCHED while bloomer v1 is built and proven. Once the bloomer is
judged ready, a separate analysis decides what in the groomer is worth keeping
before any retirement or repoint. Supersedes this task's earlier
delete-at-landing intent; the repoint work is an explicit follow-up.

## [2026-07-24 13:05 CEST] Decision-NNN: Launch sizing stays in the pipeline; the bloomer feeds it
#bloomer #launch-sizing #model-effort #pipeline

Operator ruling (2026-07-24, plan gate): the existing launch-sizing round
(Decision-019 model/effort scaling) remains part of the handoff pipeline —
removing it would be a regression. Bloomer v1's convergence report carries a
launch-sizing recommendation (size class + suggested tier) feeding that round.
Only MEASURED/statistical launch sizing remains future work (the recorded
future ruling on removing per-role defaults is unchanged).
