- created: 2026-07-28
- created_by: Sebastien Lambla
- created_during: gardener

# GitHub projection: feature = parent issue, real sub-issues, unfiled triage — Decision-119 built

## Proposal

Task of feature **Feature creation**. Implement Decision-119 in
`tools/board_gh.py`: a feature projects as a parent issue carrying the full
design; task issues attach as native sub-issues at mint, across disconnected
rounds, to the same still-open parent; the parent closes only on the operator's
delivered ruling; one-offs are flat issues; issues born on GitHub are UNFILED
and triage assigns them to a feature or one-offs before a board line exists.

Scope, all within `board_gh.py`:
- A Feature object beside `Task` (`:88`); push creates/updates the parent issue.
- Sub-issue attachment via the GraphQL path `sync_relationships` (`:357-378`)
  already uses for `blockedBy` — children become real sub-issues, replacing the
  markdown "Sub-tasks" body text (`:159-172`).
- Pull: GitHub-born issues minted as UNFILED instead of top-level `feature`
  lines (`:542-552`), feeding the triage step.

Depends on board-grammar for the feature badge it reads; the two tasks may land
in either order if the interface (what a feature line carries) is agreed first.

## Questions

1. The operator observed the existing triage UI is buggy — is fixing it in scope
   here, or is a broken-triage finding simply reported for a follow-up task?

## Findings

Inventory references in the feature sidecar (`features-first-class.md`
§Findings, "The GitHub projection").

## Testing

Push+pull round-trip against the real kaukea/orchids repository on a throwaway
feature: parent minted once, sub-issues attached, unfiled pull produces no
top-level line; then the throwaway closed.
