- created: 2026-07-20
- created_by: Sebastien Lambla

## Blockers

- None — the board and sidecars already hold the data; this is a projection of them.

## Questions

- File format and location: one file per repo (e.g. under `docs/` or `.git/`?) — it must
  be readable without launching a session, and committed state is what Orchard trusts.
- Update cadence: refreshed on every board commit (cheap, always current) or on session
  close? A stale summary silently misrepresents the repo — staleness must be detectable
  (e.g. embed the board SHA it was derived from).
- Exact payload: counts (pressing / broken / blocked), prepared next tasks with sizes,
  cross-repo dependencies — what else does the view need ([[orchard-view]])?

## Findings

- Operator (2026-07-20): "a simple available file that can be read and parsed by that
  component" — each repository's gardener PREPARES the summary; Orchard only reads.
  This keeps Orchard dumb and the intelligence where the context is.
- The projection rule already exists at task level (sidecar → board badge); this is the
  same move one level up (board → fleet summary).

## Proposal

The gardener maintains a machine-readable summary file as part of its board
commits: repo identity, per-urgency counts, blocked items with what blocks them
(including cross-repo edges), the prepared/plan-ready tasks with one-line descriptions,
and the board SHA + timestamp it reflects. Format settled at blooming (answer the
Questions first).

## Testing

Parse the file from outside any Claude session and reconstruct the repo's headline state;
diff it against the live board — no divergence at the recorded SHA.
