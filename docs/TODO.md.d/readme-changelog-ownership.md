- created: 2026-07-19
- created_by: fable-5

## Blockers

_None._

## Questions

- ~~Does the gardener write these at close, or the groundskeeper under
  instruction?~~ Settled (Decision-034, 2026-07-21): NEITHER re-derives. The
  landscaper stages the CONTENT verbatim in its sidecar result while context is
  hot; the gardener writes the FILE at ingest — placement, format, merge and
  operator gate only, never rewriting. Groundskeeper stays verify-only.

## Findings

- The single-writer rule today names only the board and `docs/decisions.md` as gardener
  owned — "child sessions do not write those directly." README and CHANGELOG are left to the
  feature branch, with the landscaper authoring and the groundskeeper verifying.
- **That does not work, evidenced 2026-07-19.** The message-bus landscaper wrote CHANGELOG
  entries by imitating existing ones without ever opening `AGENTS.files.md`, and edited the
  README without loading `readme-sync` — the skill its own close gate names. Both were
  specified; both were skipped; the output looked plausible.
- These are repo-level integration artifacts, the same category as the board and decisions: a
  feature-scoped agent sees one feature and writes them from that vantage, which is exactly
  why the board was made gardener-owned in the first place.

## Proposal

Per Decision-034: landscapers stop editing CHANGELOG.md and README.md. Their close
gate instead STAGES the content — the changelog entry in their own words, the
user-facing README delta — as blocks in the sidecar result. The gardener
promotes both intact at ingest (canonical format, parallel-feature merge,
readme-sync judgement, operator gate). Implementation is workflow-component
(landscaper def close gate, AGENTS.shared Close gate, workflow-complete presence
checks, handover ingest steps) — gardener builds directly on an operator go.

## Testing

A feature closes without its landscaper having edited either file, and both are correct
afterwards. Wired 2026-07-21 (all six contract points: landscaper def, close gates in
AGENTS.shared + workflow-complete, groundskeeper presence checks, handover ingest,
§Sidecar/§Changelog formats); marked functional pending the agreed live confirmation —
the NEXT feature close runs the staged path end to end (session-naming is nearest).
