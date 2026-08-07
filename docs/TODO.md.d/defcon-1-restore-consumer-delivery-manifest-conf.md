- created: 2026-08-07
- created_by: gh-ingest
- created_during: interactive

## Blockers
- None known yet.

## Questions
- Ingested from GitHub issue #299 — needs triage: type, component,
  urgency, scope.

## Findings
- Filed on GitHub (https://github.com/kaukea/orchids/issues/299); original body preserved below.

Every consuming repository lays its .claude tree by reading manifest.conf out of its vendored orchids clone (the kauk stopgap lays nothing without it). The de-vendoring of 2026-07-28 (ceca7ae, Decision-122) deleted manifest.conf from this package with no replacement shipped, so consumers either freeze on stale mirrors or sync into dangling links — SignMc synced on 2026-08-07 and now carries 57 dangling links; four other consumers checked are frozen on pre-rewrite copies.

Restore, per operator order (P0):

- manifest.conf back at the package root, regenerated from the tree by a committed generator so the index can never silently drift from the content again.
- An integration test that creates a brand-new project, installs the package into it with kauk, and verifies every skill, agent, hook, tool, template and rule file lands in the right position with no dangling links.
- A GitHub Actions workflow that runs that integration test.
- No further work until the tests pass.

