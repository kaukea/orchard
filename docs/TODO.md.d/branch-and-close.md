- created: 2026-07-28
- created_by: Sebastien Lambla
- created_during: gardener

# Branch and close naming: f/<feature>/<task>, archive tags to match — Decisions 116 and 120 built

## Proposal

Task of feature **Feature creation**. Implement Decision-116 (short-lived task
branches off main named `f/<feature>/<task>`, no feature branches ever) and
Decision-120's tag half (archive tags mirror branch names,
`archive/<feature>/<task>`; changelog stays flat between releases).

Scope:
- `skills/workflow/SKILL.md`: branch naming, worktree paths, and the removal of
  its line 87 — "The chosen task's `{#id}` becomes the `<feature-id>`" — the
  single most explicit statement of the conflation this feature kills.
- `skills/workflow-complete/SKILL.md` and `agents/groundskeeper.md`: tag naming,
  squash and integrity-verify paths, cleanup of `<feature>/<task>` refs.
- `agents/supervisor.md`, `agents/landscaper.md`, `agents/gardener.md`: every
  branch/worktree reference updated; the supervisor's one-worktree-per-feature
  contradiction (its lines 20-22 versus 64-65) resolved in favour of
  one-worktree-per-task under a long-living feature.
- Worktree path convention for nested branch names decided and applied
  consistently with `courier.py`'s worktree-derived identity (see Questions).

Out of scope: the board grammar, the GitHub projection, the changelog release
structuring (release-cut owns that), the team runtime design (Decision-121 —
only its branch/worktree mechanics land here).

## Questions

1. Worktree directory naming for `f/<feature>/<task>`: nested directories under
   `.claude/worktrees/<feature>/<task>` versus flattened `<feature>--<task>`.
   `courier.py:371` derives identity from the worktree directory name; the choice
   must not break it.

## Findings

`migrations/2026-07-27-unvendor-self.md` records that `courier.identity_of()`
once returned `task_id`/`task_name` (Decision-108 implemented) and lost them in
the transport rewrite — recoverable from `tools/courier.py` git history if this
task's worktree choice wants to restore the pair.

## Testing

A scripted dry-run close over a scratch branch named to the new scheme: create,
squash, tag, verify, clean — plus the existing close-path tests if any cover
naming.
