- created: 2026-07-20
- created_by: Sebastien Lambla

## Blockers

- ⊘[[bus-finishing]] (operator ordering, 2026-07-25): starts immediately when
  the bus lands, alongside the supervising controller
  ([[close-family-fakes]], Decision-090).
- Co-designed with [[fleet-sidebar]] (shared layout); reshapes what remains of
  the close choreography after Decision-090 re-homes it.

## Written-spec gate (operator, 2026-07-25 — Decision-090)

"This time I want this written down": the tmux behaviour — window creation,
naming, closing, focus return, pane stacking — ships as a COMMITTED SPEC the
operator reviews before/with the build; chat convention and skill prose do
not count. Window rename has NEVER worked (operator, 2026-07-25 morning);
the spec starts from his requirements, not the incumbent mechanics.

## Questions

- ~~Does closing the landscaper window on completion ride the groundskeeper's return
  instead of a Stop-hook countersign match?~~ Resolved by [[hook-choreography]]: the
  close rides the courier `finished` signal (Decision-028); the Stop hook is retired.
- ~~Pane lifecycle for coders: bounded how?~~ Resolved by the 2026-07-21 refinement:
  sowers stack in a dedicated RIGHT COLUMN of the landscaper's window, capped —
  the exact cap is a build-time knob (voluntary deferral), not a scope question.
- ~~Is tmux-topology the home of the NAMING REWORK?~~ RULED (operator,
  2026-07-26): a separate standalone task — [[tmux-naming]], tmux
  integration/extraction completing the existing tmux work; this spec only
  interfaces with it and its naming chapter defers to it.
- ~~Question-broker popup surface: spec'd here or in operator-interacting?~~
  RULED (operator, 2026-07-26): operator interaction is designed SEPARATELY
  in [[operator-interacting]] — it specifies WHAT it does, and the transport
  can be tmux OR plain OR any other interaction transport. This spec stays
  silent on popups; tmux is at most one transport gh#219 may choose.
- ~~Focus return: encode gh#216's two-part rule now?~~ RULED (operator,
  2026-07-26): the spec states only the simple rule — a finish selects the
  gardener window; the view-following nuance stays [[focus-returning]]'s
  own open follow-on (gh#216).

## Findings

- Operator topology ruling (2026-07-20): SESSION per repository → WINDOW per landscaper
  (one per active task) → stacked PANE per coder/sub-agent, each visibly showing what it
  is doing. On task completion the landscaper's window closes and focus returns to that
  session's gardener window.
- This supersedes Decision-006 (landscapers as panes beside the gardener) AT LANDING —
  record the formal supersession in `docs/decisions.md` on the implementing branch, not
  before; Decision-006 governs live behaviour until then.
- Current mechanics this replaces: `.return-window` + the landscaper-close Stop hook
  (see [[hook-choreography]] — the 2026-07-20 flush-race diagnosis and the /tmp leak).
- Operator refinement (2026-07-21): landscapers — the sessions the operator interacts
  with — are NEVER side-by-side/horizontal panes; one WINDOW each. A given landscaper's
  sower subagents stack in a dedicated COLUMN OF THEIR OWN on the RIGHT of that
  landscaper's window (vertical stack within the column, capped) — NOT appended below
  the landscaper (the default `split-window -v` behaviour, unusable today).
- [[hook-choreography]] landed the courier-driven close (Decision-028); its teardown kills
  the `arch:<id>` pane by TITLE (window closes if it was the last pane), so the close
  choreography survives this task's window-per-landscaper move unchanged.
- Decision-090 (2026-07-25) supersedes the "close choreography survives unchanged"
  reading above: the close re-homes to the gardener's groundskeeper (Decision-054
  staging-fold mechanics survive, re-homed); the `arch:<id>` title-kill teardown is
  replaced, not preserved.
- From [[sidebar-titling]] (live-tested 2026-07-25): `allow-rename off` governs the
  WINDOW name only; an OSC 2 write still clobbers `pane_title` even with both rename
  options off — the salvage was reverted. The spec's naming/titles chapter must give
  the pane-title mechanism (persist/re-assert, or a title hook). Its naming tail
  ("window names `<repo>/<name>`, session named 1:1 to the repo, stable pane titles")
  folds into this task's naming Questions.
- From [[bus-finishing]]: the question-broker (tmux popup) is a consumer of the
  transport, not a bus subject — its surface belongs to the tmux/operator-interaction
  side; exact home pending the operator's answer below.

## Proposal

Write the committed tmux spec (Decision-090) and make the raw layer implement it:
session per repository → titled window per landscaper → sower/coder dispatches split
stacked panes in a dedicated capped right column. Ownership per Decision-090: the
GARDENER creates and releases the landscaper's window (its groundskeeper fires on the
landscaper's `finished` or detected death, releasing worktree, branch, window in
reverse creation order); the landscaper is a pure scope — its sower panes die inside
it before exit, it touches no window; `.return-window` retires. The naming chapter is
co-designed with the operator via explicit Questions (standing ruling: prior naming
schemes rejected), inheriting sidebar-titling's pane-title tail. Co-designed with
[[close-family-fakes]] (the supervising controller — shared trigger, Decision-090).

## Voluntary deferrals

- Right-column sower cap VALUE: build-time knob, not a scope question.
- Live confirmation of the 2026-07-21 private-server mechanics on a real landscaper
  spawn rides the build, not this prep round.
- Whichever of {naming rework, popup surface, focus-return split} the operator rules
  OUT of scope becomes a linked deferral to its owning task at that moment.

## Testing

One repo session with two landscaper windows, one dispatching two coders: panes stack and
are readable; completing one task has the GARDENER's groundskeeper close only that
window and land focus on the gardener; the other landscaper is undisturbed.

Mechanics verified 2026-07-21 on a private tmux server (Decision-036 build):
window-per-landscaper spawn, title-based pane kill closes the window and returns focus,
peek panes open in the right column, stack, persist, and render transcript text
(tools/peek.sh). Marked functional pending the live confirmation: the next real
landscaper spawn runs the new-window path.

## Result

Result: done — the committed tmux spec and the raw-layer conformance for its window
plane landed on f/tmux-topology.

- branch: f/tmux-topology · HEAD b96098b · base 9452ee1
  - 79bcb19 🎉 docs/tmux-topology.md — the committed spec
  - f469d43 gardener stamps @gardener_id on its own window at boot
  - b96098b landscaper-teardown.sh window-kill primitive + ARCHITECTURE.md
- Tested (agreed method — live private tmux server, Decision-036 style): 8/8 assertions
  passed. Two landscaper windows plus two peeks stacked in feat-a's dedicated right
  column; teardown of feat-a closed ONLY its window, returned the attached client's focus
  to the gardener window, and left feat-b undisturbed; both refuse conditions (unresolved
  handle; landscaper window == gardener window) fired. Harness:
  `.git/the-works/tmux-topology/live-test.sh` (uncommittable). tools/peek.sh verified
  conformant to spec §5 by reading — no change needed.
- Delegation: discovery 5 explorers + 1 inline reconciliation; build 2 builders + 2 inline
  steps. Builders ran as `general-purpose` because the `builder`/`sower` agent type was not
  registered in the runtime (the orchard/bus→courier migration stripped the registry
  mid-session). Inline: the spec (core design) and peek-verify + ARCHITECTURE (a no-op
  verify and a delicate shared file kept under direct control to stay disjoint from
  [[close-family-fakes]]).
- Scope seam settled with [[close-family-fakes]] over the courier: window plane = mine
  (spec + tmux primitives + @gardener_id + how a window is killed); control plane = theirs
  (supervisor, close firing, reverse-order orchestration, the landscaper.md "pure scope /
  no self-teardown" edit). Edits kept to disjoint sections of the shared files
  (gardener.md, ARCHITECTURE.md).

## Changelog entry

Added a committed specification for the fleet's tmux layout (`docs/tmux-topology.md`): one
tmux session per repository, one window per active feature (the landscaper), and headless
workers (sowers) that are hidden by default but can be peeked into a capped, stacked
right-hand column. It writes down, for the first time, how a feature window is closed and
how the operator's focus returns to the gardener afterwards (the Written-spec gate,
Decision-090).

Changed: the gardener now stamps a stable `@gardener_id` marker on its own tmux window at
start-up, mirroring the `@landscaper_id` marker it already places on each feature window, so
the teardown tool can reliably find the gardener's window to return focus to. And
`tools/landscaper-teardown.sh` is now a self-contained window-kill and focus-return
primitive: it locates the feature window and the gardener window by those stable markers,
returns the operator's focus to the gardener, then closes the feature window and its
sidebar. It no longer reads the retired `.return-window` marker file, accepts an optional
tmux socket so the close worker can invoke it from outside the session, and refuses to run
when a window cannot be resolved or when closing would target the focus-return window
itself.

## Readme delta

No README change. This feature is internal workflow mechanics (agent charters and a tmux
teardown script) plus a new internal design document under `docs/`. It adds no user-facing
command, CLI flag, build step, or developer-tooling requirement — none of the readme-sync
triggers fire. (Evidenced no-change determination.)

## ARCHITECTURE determination

ARCHITECTURE.md WAS updated (the tmux/window prose in the sidebar section): `@gardener_id`
added alongside `@landscaper_id`, the window-kill primitive, the reverse-order release of
window + branch + worktree, the `.return-window` retirement, and a pointer to the committed
spec. Trigger fired: "how modules/components connect (data flow, wiring)" — the window
release is re-homed onto the gardener's groundskeeper (Decision-090) and a new
`@gardener_id` handle is introduced. Kept disjoint from [[close-family-fakes]]'s
roles-table/close-flow edits.

## Decision entries

(unnumbered — the housekeeper assigns the next free number at fold; Decision-NNN below)

Decision-NNN: The tmux topology is a committed spec; the window-kill primitive and the
@gardener_id handle land the window side of Decision-090
#tmux #topology #window #close #teardown #landscaper #gardener #spec #decision-090

- `docs/tmux-topology.md` is now the committed authority for the fleet's tmux layout
  (session per repository, window per landscaper, headless-but-peekable sowers in a capped
  right column, closing and focus return). Chat convention and skill prose no longer govern
  — the Written-spec gate of Decision-090.
- The gardener stamps `@gardener_id` on its own window at boot (value = its session id), the
  mirror of `@landscaper_id`. Both are tmux window user-options and the only load-bearing
  handles; pane titles are clobbered live by the running program (Decision-048).
- `tools/landscaper-teardown.sh` is a pure window-kill + focus-return primitive keyed on
  those handles, callable by the gardener's groundskeeper (optional socket argument) or
  self-called from within the landscaper's tmux. It retires the `.return-window` marker and
  refuses on an unresolved handle or when the landscaper window is the focus-return target.
  This lands the WINDOW side of Decision-090's reverse-order release; the close firing and
  orchestration, and the landscaper's "pure scope / no self-teardown" edit, land with
  [[close-family-fakes]].
- Formally supersedes Decision-006 (architect beside the orchestrator in a pane) at landing
  — already superseded in principle by Decision-036.
- The window-name separator alignment (the creator writes `▸`, the sidebar navigator
  resolves `/`) and the pane-title persistence mechanism are the coordinated rework of
  [[tmux-naming]]; this spec declares the naming contract only.

## Follow-ups returned to the orchestrator

- [[tmux-naming]] owns: aligning the window-name separator (`▸` vs the navigator's `/` — a
  live navigation mismatch found in discovery) and the pane-title persistence mechanism.
  This spec declares the contract and defers the mechanism, per the 2026-07-26 ruling.
- [[close-family-fakes]] owns (co-designed, seam agreed): the supervising controller, the
  groundskeeper's close firing and reverse-order orchestration, and the landscaper.md edit
  making it a pure scope that runs no self-teardown. My window-kill primitive stays
  backwards-compatible (self-callable) until that lands.
- Full real-fleet live confirmation (an actual gardener spawning an actual landscaper and
  closing it against the operator's own client) rides the next real landscaper spawn — the
  standing voluntary deferral in Testing above; the private-server test covers the mechanics.
