- created: 2026-07-27
- created_by: fable-5
- created_during: main

# Sidebar redone fresh: pruned and rewritten, with the standing rulings as its specification

## Blockers

- none — the `⊘transport-test-reconciling` blocker is REMOVED by the operator's
  2026-07-27 ruling that the sidebar derives names from EVENTS, not from the marker.
  See `## Proposal`. The two tasks are now independent.

## Questions

- ~~What "teamwork functionality" means concretely on the side window.~~ **CLOSED
  2026-07-27 — removed from this round entirely.** Operator: *"Keep those proposals for
  later, i want to fix the rendering of now."* Then, asked whether the existing agent
  and subagent rows were at least in scope as a rendering fix: *"Nothing team-related at
  all."* The four candidate meanings are recorded under EXPLICIT VOLUNTARY DEFERRALS.
- ~~Which aesthetic complaints are in this round.~~ **CLOSED — all of them, plus five
  the operator added.** See `## Proposal`.
- ~~How far the refactor goes.~~ **CLOSED — renderer plus the tmux surface.** Operator
  selected "Renderer + tmux only" and separately ruled the courier out of scope.
- **The operator's own `docs/SPECIFICATIONS.md.d/Flow.md` is EMPTY** (created 2026-07-27
  06:49, zero bytes). It did not gate this round. Operator instruction during the round:
  *"The rules have been specified multiple times. read them or build them first with
  me."* — the specification is `docs/decisions.md`, not a new document.
- **OPEN, needs a ruling before build:** Decision-058 says *"No animation anywhere"*;
  Decision-078 blesses *"band animation"* and carries the KITT-scanner tail as licensed
  debt. The live screen shows both a spinner-cycled task glyph and a KITT strip. These
  cannot both stand. Surfaced rather than quietly dropped, per the scope ruling.

## Findings

### Measurement (bloom round, 2026-07-27)

- **Convergence: overall SE 0.740 — band `lower`.** Seven dimensions; two converged
  (`rewrite_strategy` SE 0.325, `transport_sequencing` SE 0.192), five stopped by
  exhaustion.
- **Launch sizing recommendation (engine): size `l`, model `claude-fable-5`, effort
  `high`.**
- **Uncalibrated-items caveat:** the engine is v1. Its 2PL item parameters
  (discrimination, difficulty) are assumed by the measuring agent, not fitted against a
  corpus. The convergence number is a relative signal, not a calibrated probability.
- **The `lower` band understates the actual certainty of the WHAT, and the reason is
  instrumental.** Three of the four misfit flags are artefacts, not operator
  inconsistency:
  - `teamwork_content` and `aesthetic_axis` are multi-select dimensions whose true
    answers are *"none of these"* and *"all of these"* respectively. The engine's
    categorical latent model assumes exactly one hypothesis is true, so neither answer
    can converge however many times it is confirmed. Both exhausted at SE 1.118 — the
    flat prior — which is the correct representation of "this dimension does not apply
    as posed", not of operator doubt.
  - `refactor_reach` genuinely oscillated, and the fault was the measuring agent's: it
    read the operator's "the courier producer is in scope" as licence to change the
    marker format, was corrected (*"courier has nothing to do with this, its a message
    bus"*), and the correction registered as a misfit against its own earlier derived
    item. The final answer — renderer plus tmux — is unambiguous.
  - `transport_sequencing`'s misfit is the moment the operator overturned the recorded
    precondition. It then converged cleanly to `avoid_seam` at SE 0.192.
- **Two items on `refactor_reach` were DERIVED, not asked** — one from the standing
  scope ruling already in this sidecar, one as weak redundant confirmation of two
  consistent prior answers. Both are flagged here because they inflate the item count
  without adding operator evidence. One of the two was subsequently proven wrong by the
  operator's correction.

### The screen itself (screenshot taken during the round, sidebar pane `main:1.1`, 42×50)

The round captured the live sidebar rather than reasoning about it. Defects observed
directly, each traceable to a ruling or to no ruling at all:

1. **Raw session UUIDs where names belong.** Feature and task rows render
   `2eaf05b6-628f-4712-8871-c16c821d6f87` and `933691a8-68cc-42c9-aece-4036563c970a`.
   Violates Decision-059 (human names authored at intake, read by every title call
   site). **Root cause ruled by the operator: the renderer must take the name from the
   event's identity envelope, which carries it on the first message from a session, and
   currently discards it at fold time.**
2. **Every feature/task pair renders twice**, the same string on a dim band and again on
   a bright row (`Close-family fakes: the supervising con` / `…c…`, `senderX` /
   `senderX`, `siblingB` / `siblingB`). **Operator note: the feature level between
   project and task is REAL and stays — it is simply not in the workflow yet**, so both
   levels currently resolve to the same string. The renderer must degrade gracefully
   when a feature has one task of the same name; today's name-drop rule does not fire.
3. **The agent identity line is injected into the MIDDLE of the five step rows**,
   splitting the sequence: `IDEATION, SCOPING, "measuring" — bloomer, DESIGNING,
   BUILDING, RELEASING`, and in the landscaper block `RELEASING` lands *below* the
   identity line. Decision-098 places the agent subscript *beneath* its task.
4. **Two different truncation rules on the same string.** The feature row cuts at
   `…supervising con` with no ellipsis; the task row directly beneath cuts at
   `…supervising c…` with one. One of the two is wrong; neither respects the pane edge
   consistently.
5. **Empty activity renders as literal empty smart quotes** — `"" — 🌿 landscaper`,
   and bare `""` rows under `senderX` and `siblingB`.
6. **An orphan activity line** — `"returned"` with no agent, no role, no owner.
7. **Branch names mangled** — `orchids@f-close-family-fakes` for branch
   `f/close-family-fakes`; the slash is flattened to a hyphen. (Operator: *"branch name
   fixes"*.)
8. **Step-band colour is derived inconsistently** — the first feature's five step rows
   sit on a lavender band, the second's on neutral grey, with no rule distinguishing
   them. (Operator: *"colour derivation"*.)
9. **The KITT sweep renders as a static grey rectangle** to the right of `SCOPING` —
   not a sweep, just a block. See the open Decision-058/078 contradiction above.
10. **No indent gutters.** Tree depth is carried by a single `▎` tick on task rows only;
    every level sits at effectively the same left edge. (Operator: *"gutters on
    indents"*.)
11. **Contrast failure on feature rows** — dark grey-purple text on a dark purple band,
    at the limit of legibility.
12. **~19 blank rows** below the content in a 50-row pane.
13. **Glyph reuse is ambiguous** — `⋮` serves both as the agent-line field separator and
    as the active-step mark.

### True colour: root cause found

The operator's *"my own terminal not on true colour for some reason"* is diagnosed.
`tmux info` reports **`RGB: [missing]`** and **`Tc: [missing]`** while
`setrgbf`/`setrgbb` are both present, with `TERM=xterm-256color` and
`COLORTERM=truecolor`. tmux gates direct colour on the `RGB`/`Tc` terminfo capability,
which `xterm-256color` does not carry, so the outer tmux downgrades to 256 colours
*before* the renderer's Decision-102 terminfo selection can matter. **Decision-102 is
therefore not met in practice on the operator's own screen**, and the fix is a tmux
`terminal-features`/`terminal-overrides` entry advertising `RGB`, not renderer code.

### Prior state (carried forward)

- `tools/sidebar.py` is **3,056 lines / 135 functions**, having absorbed
  `tools/sidebar_model.py` (deleted by `e4e3841`).
- Test-suite blind spot: `tests/test_sidebar.py:122` hand-authors the marker it reads, so
  no test crosses the producer/consumer seam — which is how 429 tests passed while task
  rows were dead on screen.
- Data already on the bus and discarded by the renderer at fold time (`_fold_sessions`):
  `identity.parent`, the `feature_id`/`task_id` distinction, `status.context_tokens`,
  `status.spend`, `status.effort`, `status.estimates`, and `_seen_ts` idle duration.

## Proposal

**OPERATOR SCOPE RULING 2026-07-27 — this is a fresh rebuild, not another incremental
round.** Prune what needs pruning and redo the sidebar fresh. In his words, what is fresh
is "code, colouring layout adjustments and tmux integration refactorings" — and "rulings
stay". The bloom round of the same day narrowed it further; both are recorded below.

### The standing rulings ARE the specification and are not re-opened

Decision-098 (five display levels — project, feature, task, agents, subagents; agents and
subagents ephemeral; only the task persists as a single row carrying its terminal state),
Decision-099 (the durable task node, one file per project-and-feature, archived rather
than deleted so a feature rehydrates), Decision-100 (retention until restart; the pruner
stays undesigned), Decision-101 (any identity earns a row, not only landscapers),
Decision-102 (exact hue via direct-colour terminfo), Decision-094 (staleness is a colour,
never a removal), Decision-058 (six static states), Decision-059 (human names authored at
intake), Decision-078 (the blessed mock is the renderer's fixed visual contract),
Decision-081 (exit-grace and `signal --on-behalf-of` deliberately removed — they do not
come back), Decision-103 (a round-trip test needs a static-data companion), and the solid
per-repo hue headers with one circle glyph family. The rewrite is judged against these,
and any it cannot meet is surfaced rather than quietly dropped — see the open
Decision-058/078 animation contradiction under `## Questions`.

### Rulings made in this bloom round (operator, 2026-07-27, verbatim where quoted)

- **Names come from EVENTS, not from the marker.** *"Don't rely on the marker for names,
  rely on events"* — *"first message from a uuid contains all that data"*. This is the
  single highest-value change in the round: it removes the dependency on
  `transport-test-reconciling` entirely and reclassifies the UUID rows as a renderer
  defect the rewrite fixes on its own.
- **The marker is a cache; everything else is realtime.** *"The marker should contain a
  cache. The rest is supposed to be realtime reading, not just rendering a pre-canned
  file every seconds???"* This refines, and does not reopen, Decision-099: the durable
  node supplies what remains when nothing is happening; live state is read from the event
  stream.
- **The courier is out of scope.** *"courier has nothing to do with this, its a message
  bus. If you find a bug, we discuss, otherwise its transport."* Bugs found in it are
  raised with the operator, never fixed inside this round.
- **The feature level is real.** *"note there is a feature in the middle of project and
  task. It's just not in the workflow yet."* The renderer keeps the level and must handle
  it being unpopulated without rendering the same name twice.
- **No teamwork functionality this round.** *"Keep those proposals for later, i want to
  fix the rendering of now"*, and then *"Nothing team-related at all"*. The word
  "teamwork" in this task's title no longer describes its scope; the title is left for
  the operator to change or keep.

### Reach: renderer plus the tmux surface

`tools/sidebar.py` and the launch/mount/peek/teardown surface — `tools/sidebar-mount.sh`,
`tools/peek.sh`, `tools/sidebar_nav.py`, `tools/bloomer-launch.sh` and the window and
pane conventions they encode. **Not** the courier. **Not** the transport. **Not** the
on-disk marker format.

### Shape: extract in place, module by module

Operator selection: the existing file is split into modules step by step, pruning dead
paths as each one comes out, with tests green between steps — not a clean-room rewrite.
Nothing is lost by accident; the cost is inheriting the old structure's shape, accepted.

### Aesthetics: every axis is in

All four axes put to the operator were confirmed in — spacing/density/row order,
colour and contrast, glyphs, truncation and fit — plus five he added unprompted:
**branch name fixes**, **colour derivation**, **gutters on indents**, **highlights**, and
**his terminal not being on true colour** (diagnosed above; the fix is tmux
configuration, not renderer code).

### Testing the seam

*"you can use the bus with a fake project and emit updates in that way, your producer
wont know the difference"* — and *"'changing' and 'touching' are different things"*: the
tests may drive the real bus without the rewrite modifying it. Decision-103 applies in
full: that round-trip test MUST be accompanied by a static-data test over fixture content
hand-validated at writing time, ideally captured from the running system — otherwise
writer and reader only prove they agree with each other, which is precisely how 429 tests
passed over a dead screen.

## EXPLICIT VOLUNTARY DEFERRALS (Decision-027)

Each of these was raised in this round and consciously left out. None is forgotten; none
is in scope.

- **All four teamwork meanings**, deferred by direct operator ruling to a later round:
  who is talking to whom (live conversation edges); who spawned whom (delegation
  parentage — `identity.parent` is already on the bus and discarded); each agent's
  current activity and how long it has been there (`_seen_ts` exists, only its binary
  staleness bucket is used); what each agent is blocked or waiting on
  (`STATUS_EMOJI["waiting"]` and `["awaiting_agent"]` exist and are unreachable).
- **Interaction beyond what exists.** The round settled on display-only; the current
  `Enter` → `sidebar_nav.navigate_to` stays as-is, and no acting-on-agents affordance is
  added. `tools/peek.sh` remains unwired to the sidebar.
- **The transport and the courier**, including the 36 red tests — they belong to
  `transport-test-reconciling` and are now genuinely independent of this round.
- **The marker's on-disk format**, fixed for this round by the courier-out-of-scope
  ruling.
- **Unrendered model data** — `Repo.tokens`, `Repo.dollars`, the `footer_lines()` /
  `done_footer_line()` formatters, `status.spend`, `status.effort`, `status.estimates`.
  Present, tested, never drawn. Not this round.
- **The pruning policy**, still deliberately undesigned per Decision-100.
- **The task's own title.** It says "teamwork" and the round removed teamwork; renaming
  is the operator's call, not the measuring agent's.

## Testing

- **Agreed in this round:** a test that emits updates onto the real bus under a fake
  project and asserts on the rendered frame, so the producer cannot tell the difference —
  paired, per Decision-103, with a static-data test over fixture content validated by
  hand at writing time.
- **Standing constraint, unchanged:** this feature is judged on the operator's screen,
  not by unit tests alone — a sidebar cannot be judged from inside the branch that
  changes it. The screenshot method used in this round (capture the live pane, read it,
  and enumerate defects against the rulings) worked and should be repeated at the build's
  acceptance rather than reserved for intake.
