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

## Proposal

Rework spawn/return choreography to the session/window/pane topology: landscaper spawns
create titled windows; sower/coder dispatches split stacked panes in that window; the
completion path (post-groundskeeper) closes the window and selects the gardener window.
Design together with [[fleet-sidebar]]; absorb or close [[hook-choreography]] with it.

## Testing

One repo session with two landscaper windows, one dispatching two coders: panes stack and
are readable; completing one task closes only its window and lands focus on the
gardener; the other landscaper is undisturbed.

Mechanics verified 2026-07-21 on a private tmux server (Decision-036 build):
window-per-landscaper spawn, title-based pane kill closes the window and returns focus,
peek panes open in the right column, stack, persist, and render transcript text
(tools/peek.sh). Marked functional pending the live confirmation: the next real
landscaper spawn runs the new-window path.
