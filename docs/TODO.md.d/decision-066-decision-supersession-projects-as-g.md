- created: 2026-07-25
- created_by: gh-ingest
- created_during: interactive

## Blockers
- None known yet.

## Questions
- Ingested from GitHub issue #231 — needs triage: type, component,
  urgency, scope.

## Findings
- Filed on GitHub (https://github.com/kaukea/orchids/issues/231); original body preserved below.

#decision-projecting #github #graphql #duplicate #supersession

GitHub's `closeIssue` GraphQL mutation has carried `stateReason: DUPLICATE`
plus `duplicateIssueId: ID` since December 2024 — confirmed against the
`octokit/graphql-schema` schema, not assumed. `gh issue close --reason` never
exposed it (CLI only offers `completed`/`not planned`), which is why an
earlier pass assumed a body-note fallback (the `~related` precedent,
Decision-053) would be needed. It isn't: reaching the native mutation is one
more `gql()` call, the same helper already used for `createIssueType`/
`updateIssueIssueType`. decisions.md has no separate "duplicate" state
distinct from "superseded" (only board tasks do, per Decision-029) — so
supersession itself projects as the native duplicate-of: the OLDER
(struck) decision's issue closes pointing at the NEWER (superseding) one,
matching the file's own `Superseded by Decision-MMM` direction.
