- created: 2026-07-24
- created_by: Sebastien Lambla

## Blockers

None for the inventory pass. Later passes (phase/era marking, graph construction)
depend on the capture spool ([[capture-now]]) staying current.

## Questions

- First-pass output review: does the catalog's era classification (never-orchids /
  early / current) match the operator's knowledge of each repo's history?
- Batch cadence and budget for the content passes that follow the inventory
  (phase-marking is the first token-costing pass).

## Findings

- Design session 2026-07-24 (blueprint + four research sweeps + two reviews, in the
  gardener workstream log): pipeline is schema-last — (1) phase + era + monotonic
  order marking, (2) extraction around the authored skeleton (decisions chains, commit
  trailers, board edges), (3) distillation with operator ratification. Indexing is
  deliberately inventory-FIRST: enumerate and measure everything before any content
  pass, because the first classification will be wrong and re-runs must be cheap.
- Expected to be re-run repeatedly; wrongness is planned for. Re-run time is the window
  in which the ledger gets built.

## Proposal

Index the fleet's entire knowledge corpus, inventory before interpretation. Pass 1
(launched 2026-07-24, background): a catalog of every source — git repos under ~/src
(era-classified by orchids markers), session transcripts, the-works channels, telemetry
notes, memory files — with counts, sizes, date ranges, and coverage gaps, written to
`.git/the-works/_capture/index/` as catalog.md + catalog.jsonl. Later passes add
phase/era marking and skeleton-anchored extraction per the blueprint; each pass stays
deterministic and re-runnable.

## Testing

- Pass 1: catalog totals spot-checked against known facts (repo count, ~30-day commit
  volume, transcript counts); coverage gaps listed explicitly rather than silently
  absent.
- Re-run produces an identical catalog on unchanged sources (determinism check).
