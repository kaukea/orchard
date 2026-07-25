- created: 2026-07-20
- created_by: Sebastien Lambla

## Blockers

- ⊘[[orchard-view]] — launch is driven by the selection the view produces.

## Questions

- "Told the selection": delivered how — spawn prompt (like the landscaper boot prompt),
  the pending-subjob marker pattern, or a courier message the booting gardener reads?
- Double-check semantics: what does the gardener verify (task still open, not newly
  blocked, board moved since the summary was written) and what happens on a mismatch —
  re-present locally, or bounce back to Orchard?

## Findings

- Operator (2026-07-20): selecting repositories creates ONE TMUX SESSION PER REPO; window
  1 of each is that repo's gardener, launched automatically — no waiting, no manual
  `orch`. The gardener is TOLD the operator's pick and DOUBLE-CHECKS it against the
  live board before handing off (the summary the pick came from may be stale).
- Picking something new instead of a prepared task drops into the normal gardener
  intake flow (create the task, bloom, then hand off) — Orchard adds no second intake path.
- The `orch` wrapper (`bin/orch`) already implements resume-or-create per repo; the
  session-per-repo spawn is its fleet-scale sibling.

## Proposal

Orchard's selection step spawns, per chosen repo: a named tmux session, window 1 running
the gardener with a boot payload naming the picked task(s). The gardener validates
the picks against the board (staleness, blockers), confirms or corrects with the operator,
then runs the standard handoff ([[handover-contract]]) for each confirmed task.

## Testing

Select two repos with one prepared task each: two sessions appear, each gardener
boots knowing its pick and confirms it; deliberately stale pick (board moved after the
summary) is caught by the double-check, not silently dispatched.
