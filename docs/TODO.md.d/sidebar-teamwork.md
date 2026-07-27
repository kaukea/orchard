- created: 2026-07-27
- created_by: fable-5
- created_during: main

# Sidebar round: aesthetics, teamwork functionality, and a refactor of the renderer

## Blockers

- none

## Questions

- **The operator is authoring the specification himself, in `docs/SPECIFICATIONS.md.d/Flow.md`.** That file is the source of this task's WHAT; no bloom round runs until it is written, and the questions below are held in case it leaves any of them open rather than asked ahead of it.
  - What "teamwork functionality" means concretely on the side window.
  - Which aesthetic complaints are in this round, and which already-ruled contracts stay untouched.
  - How far the refactor goes — the internals of `tools/sidebar.py` only, or its seams with `courier.py` and the transport too.

## Findings

- Operator framing at intake (2026-07-27): "one more round in clearing up the side window, purely aesthetics and teamwork functionality, as well as refactoring."
- `tools/sidebar.py` is now **3,056 lines / 135 functions**, having absorbed `tools/sidebar_model.py` (deleted by `e4e3841`) and several successive rounds. Size alone makes the refactor axis real rather than cosmetic.
- Prior rounds and their standing rulings — this round amends, never silently re-litigates: `sidebar-polish`, `sidebar-fixes`, `sidebar-empty-rows` (Decision-098 five-level display, only the task persists; Decision-099 durable task node), `sidebar-titling` (closed superseded), Decision-081 (exit-grace and `signal --on-behalf-of` deliberately removed), Decision-102 (exact hue via direct-colour terminfo).
- **Precondition:** the messaging restoration (`transport-test-reconciling`) is unbuilt, and the sidebar reads the transport it repairs. Building sidebar work on the current broken bus would be building on sand — sequence this round after it, or scope this round to parts that do not touch the transport seam.
- Test-suite blind spot inherited from the report: no test crosses the producer/consumer seam (`tests/test_sidebar.py:122` hand-authors the marker it reads), so renderer tests can pass while the feature is broken on screen. Any refactor here should close that gap rather than inherit it.

## Proposal

- **Awaiting the operator's own specification** in `docs/SPECIFICATIONS.md.d/Flow.md`. Three axes named at intake: aesthetics, teamwork functionality, refactoring. That file is folded in here as the Proposal once he has written it.

## Testing

- To be agreed in the bloom round. Note the standing constraint: this feature is judged on the operator's screen, not by unit tests alone — a sidebar cannot be judged from inside the branch that changes it.
