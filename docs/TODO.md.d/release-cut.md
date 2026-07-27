- created: 2026-07-27
- created_by: Sebastien Lambla
- created_during: gardener session (post-close round, sidebar-empty-rows)

## Blockers

- OPERATOR HOLD (2026-07-27): "no release yet" — said at the opening of the
  Decision-050 bloom round, before the first question was answered. The cut
  does not proceed until the operator lifts the hold.

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
- Bloom round of 2026-07-27 (04:54): halted by the operator at the first
  question ("no release yet") — zero of the four scoped dimensions measured;
  every entry under Questions remains open. Engine state kept at
  `.git/the-works/release-cut/bloom-state.json` for a successor round.
- Scoping facts from that round: the repository carries NO version tag (only
  `archive/*` tags), so any cut is the first ever; the stopgap kauk CLI has
  no tag/version awareness — a consumer-facing version pin would be new kauk
  capability, not configuration.

## Proposal

(unconverged — the 2026-07-27 bloom round was halted by the operator hold
before any measurement; WHAT the release delivers, its version, and which
staged changelog admissions ride it remain open in Questions)

## Testing

(set at bloom/plan — how the cut is verified: tag present, changelog
rolled, a consuming repository's sync sees the released version)
