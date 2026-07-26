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
- Is tmux-topology the home of the NAMING REWORK — session/window/pane naming scheme
  designed with the operator, inheriting sidebar-titling's tail — or a separate task
  this spec only interfaces with?
- Question-broker popup surface: does this spec define the popup primitives (with
  [[operator-interacting]] gh#219 consuming them for exchange semantics), or does the
  whole broker UI stay in operator-interacting?
- Focus return: does the spec encode [[focus-returning]]'s two-part rule (finish
  always SELECTS the gardener window; visible focus switches only when the operator
  sits in the closing window) — confirming that rule now — or stay with the simple
  "selects the gardener window" and leave gh#216 as the follow-on?

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
