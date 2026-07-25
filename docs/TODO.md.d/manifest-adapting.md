- created: 2026-07-25
- created_by: Sebastien Lambla
- created_during: orchestrator session (orchard-renaming ingest)

## Blockers

- EXTERNAL: kauk ships the manifest retirement first. The work itself is
  kauk's (`kauk docs/TODO.md.d/manifest-by-convention.md`, moved there
  2026-07-20); this task only adapts orchids afterwards.

## Questions

- None until kauk's specification exists — "adapt to the actual specification"
  (operator): the orchids-side shape is read off what kauk actually ships, not
  designed in advance.

## Findings

- OPERATOR ORDER (2026-07-25, verbatim flow): fill in the details of the work
  to do → switch to kauk, update it there → publish → come back to orchids and
  adapt to the actual specification. Manifest retirement is managed BY KAUK.
- PAYLOAD TO CARRY TO KAUK (the "details of the work to do", staged here until
  the switch): the operator's mid-build ruling escalates the cancelled
  lint+derive plan to full RETIREMENT — kill `manifest.conf`. kauk derives the
  delivery from the tree + conventions instead of a hand-typed index:
  - `skills/<name>/` → skill entries; role from skill frontmatter
    (`roles:` already exists — role-dag-frontmatter shipped it).
  - `tools/`, `hooks/`, `agents/` → link entries by location convention.
  - `templates/` → template entries; prefix blocks by convention or a tiny
    per-file marker.
  - Known manifest failure mode this kills: silent drift — 2026-07-19, four
    committed+tested files were distributed to nobody for four missing lines;
    nothing reconciles the index against the tree.
  - Per-repo tuning stays in `.ai.toml` (exclude|copy|link|local) — unaffected.
- orchids' `manifest.conf` today: 60 lines, four line types (skill/link/
  template/prefix), parsed by the kauk-sync stopgap with a bare grep.

## Proposal

After kauk publishes the retirement: delete `manifest.conf`, verify a fresh
`kauk sync` delivers the identical file set from convention alone (diff the
`.claude/` laydown before/after), and update ARCHITECTURE.md's repo-layout
line. Nothing else changes on the orchids side unless kauk's shipped spec
demands it.

## Testing

To agree when scoped — expected: `kauk sync` on a consumer repo with the
manifest gone reproduces today's laydown exactly; a deliberately added new
skill file is delivered WITHOUT any index edit.
