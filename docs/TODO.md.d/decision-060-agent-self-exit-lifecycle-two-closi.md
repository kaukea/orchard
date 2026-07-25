- created: 2026-07-25
- created_by: gh-ingest
- created_during: interactive

## Blockers
- None known yet.

## Questions
- Ingested from GitHub issue #229 — needs triage: type, component,
  urgency, scope.

## Findings
- Filed on GitHub (https://github.com/kaukea/orchids/issues/229); original body preserved below.

#lifecycle #close #sidebar #reaping #sidebar-polish

From the sidebar-polish build (operator, direct), the real fix for stale
sidebar rows: agents END via a lifecycle contract — two closing messages
and a declared grace period (default 10s); past the window the
orchestrator kills the process and broadcasts the death. Distinct from
bus-singleton (which reaps stray bus sidecars, not whole agents).
