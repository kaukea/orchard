- created: 2026-07-28
- created_by: Sebastien Lambla
- created_during: gardener

# Features first-class: land Decision-105 everywhere, not just the sidebar

## Proposal

Operator, 2026-07-28: *"We're going to make features a first level concept in all of
the work we do."* Confirmed at intake as landing Decision-105 across every surface —
board, sidecars, branches, worktrees, supervisors, the close, and the GitHub
projection — rather than the display alone.

Decision-105 (2026-07-26) already ruled the model: the tree is
`area -> component -> feature -> task -> step -> agent -> subagent`, a feature spans
many tasks, and — the operator's words — *"every artifact still assuming [feature ==
task] is wrong."* That ruling was applied to the sidebar renderer and nowhere else.
This task is the rest of it.

## Blockers

None on the reading side. The shape of the feature object is the operator's to set —
`docs/TODO.md` is a file format, and file formats are his sole responsibility
(Decision-115's own framing). The bloom round is where that shape is converged.

## Findings

**Where feature == task is still assumed.** Read off the live tree at `ceca7ae`:

- `docs/TODO.md` — a flat list of TASKS. `feature` appears only as one value in the
  badge's type field (`feature · bug · refactor · housekeeping · completion`), which
  makes it a peer of `bug`, not a container of anything. Nesting is expressed by
  two-space indentation and `~edge` tags; neither creates a feature node.
- `docs/TODO.md.d/<id>.md` — one sidecar per task. A feature has no sidecar, so it
  has nowhere to carry its own scope, its own testing agreement, or its own state.
- Branches and worktrees — `f/<id>` and `.claude/worktrees/<id>` are created per
  task. The `f/` prefix already says "feature" while naming a task.
- The supervisor — one per feature in its charter, one per task in practice, because
  the gardener hands off a single board line.
- The close — the groundskeeper squashes one branch and flips one board badge, so a
  feature spanning several tasks has no moment at which it is itself complete.
- `board_gh.py` — the GitHub projection maps a board line to an issue. A feature
  spanning many issues has no representation beyond the `~edge` tags.
- `CHANGELOG.md` — one entry per closed task, so the reader sees the parts and never
  the feature.

**Already correct and usable as the reference implementation:** the sidebar's orchard
marker (Decision-099) is keyed `(project, feature)` and holds the tasks under that
feature with their states. It is the one place a feature is already a durable object.

## Questions

Converged by the bloom round with the operator; recorded here as they are settled.

## Testing

To be agreed at scope. The board is machine-checkable — `board_lint.py` reads the
badge grammar — so a format change has a real verification surface.
