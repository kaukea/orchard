- created: 2026-07-21
- created_by: fable-5 (gardener, agent-closing ingest)

## Questions

- None — mechanical reconciliation.

## Findings

- Flagged by the agent-closing landscaper (not touched, decisions.md is the
  gardener's): `skills/*.md` cite "Decision-046" (worktree-mode) and
  "Decision-047" (metadata-hints) with meanings that differ from
  `docs/decisions.md` 046 (courier wake) and 047 (operator relay) — the skills
  were written against a different numbering.

## Proposal

Sweep `skills/*.md` for `Decision-0NN` citations, map each to the decision it
actually means in `docs/decisions.md`, and correct the numbers (or replace
with the decision's title where a number is ambiguous). No behaviour change.

## Testing

Grep sweep: every `Decision-0NN` citation in skills/ resolves to a
decisions.md heading whose subject matches the citing sentence.
