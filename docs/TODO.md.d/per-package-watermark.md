# Per-package migration watermark

`bug · todo · critical · working · process`

## Problem

Every kauk-managed repository on the machine except kauk itself was frozen at orchids
`76ee635`, 230 commits behind, still resolving names renamed away weeks earlier
(`skills/git-commit`, `skills/gardener`, `agents/groomer.md`). Twelve orchids migrations
existed to converge exactly those renames. Not one repository had ever been told.

Two defects, both in the watermark rather than in migrations:

1. The pending-notice hook read only the consuming repository's own `migrations/`
   directory (`for d in "$root/migrations"`), never the installed packages'. A pure
   consumer has no such directory, so the notice never fired at all — for any package.
2. A single `the-works/migrated` file held a single basename for the whole clone. With
   several packages installed the last writer hides the rest; kauk's file held an
   *orchids* basename while kauk's own migration went unannounced.

## Result

The watermark is a directory keyed like every other package reference,
`the-works/migrated/<owner>/<repo>`, one file per package holding that package's last
applied migration basename. Absent = everything pending for that package. Packages are
independent and are applied one after another.

Identity comes from the vendoring path (`.ai/repositories/<owner>/<repo>`), and for a
repository's own migrations from its `origin` remote — which handles both the GitHub
remotes and the local-path remotes in use here.

Shipped:

- `hooks/migrations-pending.sh` — new; walks the repo's own `migrations/` plus every
  `.ai/repositories/*/*/migrations/` and reports each package's pending set separately.
- `settings.json` — repointed at the script, following the existing script-hook pattern
  rather than growing the inline one-liner.
- `AGENTS.files.md` §Migrations — Watermark and Execution paragraphs rewritten in place,
  no net growth.
- `migrations/2026-08-11-per-package-watermark.md` — converts the bare file to the keyed
  directory, attributing the existing basename to whichever installed package's
  `migrations/` actually contains it, and discarding it when none does.
- `tests/test_migrations_pending.py` — 11 cases.

See Decision-143.

## Testing

`python3 -m pytest tests/test_migrations_pending.py` — 11 passed. The conversion script
is extracted from the migration document by the test rather than copied, so the text that
ships is the text under test.

Full suite: 41 failed / 509 passed on this branch against 41 failed / 498 passed on clean
`main` — the same pre-existing failures (`test_orchard_transport`, `test_sidebar_*`), plus
the 11 new cases. No regression.

Live check against the kauk repository, which has two packages installed: the notice
correctly reported `serialseb/kauk` with 1 pending and `serialseb/orchids` with 12 — none
of which the old hook had ever surfaced.

**Acceptance test still outstanding** (operator's plan): move kauk to the `kaukea`
organisation and bring every consuming repository forward through this mechanism. Until
that runs, this is verified by fixture and by one live read, not by a real estate
migration.

## Changelog entry (staged, verbatim — Decision-034)

- 🐛 **Consuming repositories were never told a migration was pending.** A survey of
  every kauk-managed repository on the machine found eleven of twelve frozen at the same
  orchids commit, 230 behind, still resolving skill and agent names renamed away weeks
  earlier — while twelve migrations existed to converge exactly those renames. The fault
  was the watermark: the pending-notice hook read only the consuming repository's *own*
  `migrations/` directory, which a pure consumer does not have, so the notice never fired
  for any package in any of them; and a single watermark file holding a single basename
  cannot track several installed packages, so whichever package advanced it last hid the
  rest. The watermark is now one file per package at
  `the-works/migrated/<owner>/<repo>` — keyed exactly as packages are keyed everywhere
  else — and the notice reports each package's pending set separately, applied one
  package after another. A dated migration attributes an existing bare watermark to
  whichever installed package's `migrations/` actually contains that basename, and
  discards it when none does, which is safe because every migration step is guarded by
  observable state and re-applying one already applied is a no-op. See Decision-143.
