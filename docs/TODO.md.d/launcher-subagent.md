- created: 2026-07-21
- created_by: fable-5
- created_during: f/app-identifying

## Blockers

- None.

## Questions

- OPEN: the operator's definition of the subagent's remit and its seam with the
  gardener was cut off mid-sentence ("in a subagent that…") in the
  app-identifying session — ask him to complete it BEFORE any plan.

## Findings

- SEAM 1 of the unified local/remote loop (see merge-ordering sidecar): the
  launcher owns the local-vs-remote check; the gardener calls it blind.
  Local → create worktree + spawn landscaper. Remote → NO-OP (runner checkout +
  f/<id> branch already exist, created by the ENGAGE prologue).
- Rationale: worktree creation + agent launching is implementation-detail
  mechanics with no cloud analogue; factoring it out mirrors the cloud's
  ENGAGE branch-creation delegation.

## Proposal

Extract the git-worktree creation + landscaper launching the local gardener
performs at handoff into its own launcher subagent, so the gardener's
handoff step is mode-agnostic.

## Testing

To agree when bloomed — expected: a local handoff through the launcher yields
the same worktree/pane topology as today; the gardener no longer runs
git worktree/tmux commands itself.
