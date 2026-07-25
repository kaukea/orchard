- created: 2026-07-25
- created_by: gh-ingest
- created_during: interactive

## Blockers
- None known yet.

## Questions
- Ingested from GitHub issue #228 — needs triage: type, component,
  urgency, scope.

## Findings
- Filed on GitHub (https://github.com/kaukea/orchids/issues/228); original body preserved below.

#naming #titles #board #sidebar-polish

From the sidebar-polish build (operator, direct): the declarative human
name (imperative-vs-declarative, session-naming contract) is AUTHORED when
the ledger entry is created — the board's short title / sidecar H1 — and
every title call site reads that; mechanical hyphen-replace survives only
pre-intake. No runtime grammar-conversion code exists.
