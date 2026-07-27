- created: 2026-07-27
- created_by: Sebastien Lambla
- created_during: gardener session (post-close round, sidebar-empty-rows)

## Blockers

(none — the holding gate, live check (a), passed at the operator's
2026-07-27 01:26 eyeball and the sidebar-empty-rows close is merged and
pushed)

## Questions

- What does the cut comprise: a version tag + CHANGELOG roll only, or also
  a consumer-facing signal (kauk-side pin, announcement to consuming
  repos)?
- Version scheme and the first number — no version tag exists in the
  repository yet; this is the first cut.
- Which changelog admissions ride the cut: the sidebar-empty-rows entry is
  staged but HELD by the operator (2026-07-27); bus-transport-v2's
  admission is still pending its operator round and its text carries a
  stale sidebar_v3 mention to fix at admission. Do either land before the
  roll, or does the cut take Work in progress as it stands?
- Does this release count as the one after which the bus→courier cutover
  shim retires (ruling of 2026-07-25 on the Decision-085 rename: the shim,
  dual-name hooks, and compat symlink ship "behind a one-release
  cutover")?

## Findings

- Trigger: the bus arc landed (e4e3841) and the release cut was held on
  live check (a) — the sidebar showing session activity end-to-end after
  the cutover. That check passed 2026-07-27; sidebar-empty-rows is
  squash-merged as 2fbc3cc and pushed.
- The operator ordered the cut on 2026-07-27 ("Cut the release").

## Proposal

(to be converged by the bloom round — WHAT the release delivers, its
version, and which staged changelog admissions ride it)

## Testing

(set at bloom/plan — how the cut is verified: tag present, changelog
rolled, a consuming repository's sync sees the released version)
