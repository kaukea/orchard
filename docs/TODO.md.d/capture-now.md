- created: 2026-07-24
- created_by: Sebastien Lambla

## Blockers

None — deliberately built with zero dependencies so preservation starts before the
ledger exists.

## Questions

- Recurring trigger: gardener-boot invocation only, or also a scheduled run so
  capture survives days with no gardener session?
- Retention of the spool once the encrypted ledger ingests it: delete, or keep as the
  pre-ledger stratum?

## Findings

- First snapshot ran 2026-07-24: 2,710 files, 709M — Claude session transcripts for
  every project plus every repo's `.git/the-works/` channel (workstream logs, mood
  snapshots). All of this was previously mortal: /tmp evaporation, provisional
  retention, overwrites.
- Incremental (rsync) and idempotent; a manifest line per run gives the spool its own
  audit trail.

## Proposal

Stop-loss preservation of the fleet's uncommitted knowledge, running from tonight until
the append-only encrypted ledger replaces it. `.claude/tools/capture-snapshot.sh`
mirrors `~/.claude/projects/` and each repo's `.git/the-works/` into
`.git/the-works/_capture/<host>/`, incrementally, with a manifest log. Invoked at every
gardener boot; the ledger (separate task, designed 2026-07-24) supersedes it. The
spool is the raw substrate the corpus-indexing task catalogs.

## Testing

- Run the script twice; second run is incremental (no re-copy churn) and appends a
  manifest line.
- Delete a test file from the spool, re-run, confirm restoration from source.
- Confirm transcripts from a non-orchids repo's sessions appear in the spool.
