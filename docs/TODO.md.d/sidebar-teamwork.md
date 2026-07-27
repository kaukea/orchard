- created: 2026-07-27
- created_by: fable-5
- created_during: main

# Sidebar redone fresh: pruned and rewritten, with the standing rulings as its specification

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

**OPERATOR SCOPE RULING 2026-07-27 — this is a fresh rebuild, not another incremental round.**
Prune what needs pruning and redo the sidebar fresh. In his words, what is fresh is "code,
colouring layout adjustments and tmux integration refactorings" — and "rulings stay".

- **The standing rulings ARE the specification and are not re-opened.** Decision-098 (five
  display levels — project, feature, task, agents, subagents; agents and subagents ephemeral;
  only the task persists, remaining as a single row carrying its terminal state),
  Decision-099 (the durable task node, one file per project-and-feature, archived rather than
  deleted so a feature rehydrates), Decision-081 (exit-grace and `signal --on-behalf-of`
  deliberately removed — they do not come back), Decision-102 (exact hue via direct-colour
  terminfo), and the solid per-repo hue headers with one circle glyph family. The rewrite is
  judged against these, and any of them it cannot meet is surfaced rather than quietly dropped.
- **Fresh: the code.** `tools/sidebar.py` is rewritten rather than patched — 3,056 lines and
  135 functions accreted across six rounds, absorbing the deleted `tools/sidebar_model.py`.
  Accumulated dead paths are pruned as part of the rebuild.
- **Fresh: colouring and layout adjustments.** Within the standing visual contract, not a new one.
- **Fresh: the tmux integration, refactored.** The launch, mount, peek and teardown surfaces
  (`tools/sidebar-mount.sh`, `tools/peek.sh`, `tools/sidebar_nav.py`, `tools/bloomer-launch.sh`
  and the window/pane conventions they encode) are refactored as part of this work.
- **Teamwork functionality** remains the one axis with no standing ruling behind it — the
  bloom round and the operator's own `docs/SPECIFICATIONS.md.d/Flow.md` define it.
- Close the producer/consumer test gap in the rewrite rather than inheriting it: today no test
  writes through `courier` and reads through the renderer, which is why 429 tests passed while
  the task rows were dead on screen.

## Testing

- To be agreed in the bloom round. Note the standing constraint: this feature is judged on the operator's screen, not by unit tests alone — a sidebar cannot be judged from inside the branch that changes it.
