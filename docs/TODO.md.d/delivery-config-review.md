- created: 2026-07-23
- created_by: fable-5
- created_during: gardener session

## Blockers

- None known.

## Questions

- None open before the audit runs; the review itself produces the AGENTS.d
  proposal and the operator validates it (Decision-071 — agents never settle a
  file format alone).

## Findings

- kauk sync flags 2 BLOCKED on every run in orchids: `AGENTS.shared.md` and
  `AGENTS.files.md` are real files where the manifest wants links; `link_one`
  (kauk `bin/kauk:149`) refuses to overlay a real file it did not place —
  per-file protective skip, the rest of the sync completes.
- kauk's own BLOCKED message suggests "mark it local/copy in .ai.toml", but
  Decision-071 rules that out: `.ai.toml` is operator-owned; agents never write
  delivery markings there. The message points at a surface the fleet no longer
  wants used that way.
- Operator assessment (2026-07-23): the current delivery-config state is a
  mess; a complete review is ordered. Per-file delivery/validation markings
  belong in `AGENTS.d`.

## Proposal

Complete review of kauk's per-file delivery configuration: audit `.ai.toml`
and every delivery marking across the installed repos, design `AGENTS.d` as
the home for per-file delivery/validation configuration (exact shape proposed
by this review, validated by the operator), keep `.ai.toml` operator-owned,
and align kauk's BLOCKED guidance with the new surface so the standing noise
on orchids' canonical AGENTS files is resolved legitimately (upstream kauk).

## Testing

To agree when bloomed; candidate: a clean `kauk sync` across all consuming
repos with zero BLOCKED/DRIFT lines and no agent-writable `.ai.toml` surface.
