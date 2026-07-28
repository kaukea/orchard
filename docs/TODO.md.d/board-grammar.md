- created: 2026-07-28
- created_by: Sebastien Lambla
- created_during: gardener

# Board grammar: two levels, two badges, One-offs — Decisions 117 and 118 built

## Proposal

Task of feature **Feature creation**. Implement Decision-117 (the board is two
levels with two badge grammars, One-offs is the empty feature) and Decision-118
(a feature's sidecar is a container file with segregated per-task sections).

Scope:
- `AGENTS.files.md` §TODO and §Sidecar rewritten to the ruled shapes, including
  the operator-accepted render in the features-first-class sidecar §2.
- `tools/board_lint.py` knows exactly three line shapes: feature line, task line,
  the single One-offs bucket. Feature badge: id, gh# parent issue, touched
  components, derived task progress. Task badge: today's six fields.
- `docs/TODO.md` migrated: existing lines regrouped under feature lines or the
  One-offs bucket, with a dated `migrations/` entry shipped in the same branch
  (the board is a managed artifact being reformatted).
- Feature container sidecars per Decision-118; one-offs keep their files.

Out of scope: branch/tag naming (branch-and-close), the GitHub projection
(github-projection), the team runtime.

## Questions

1. Which existing board tasks group under which features at migration time — the
   grouping needs the operator's eye before the migrated board is committed.

## Findings

The full inventory of feature==task assumptions is in the feature sidecar
(`features-first-class.md` §Findings), with `board_lint.py` line references.

## Testing

`board_lint.py` clean over the migrated board; round-trip: every pre-migration
task line present exactly once post-migration (scripted count, not eyeballed).
