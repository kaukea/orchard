- created: 2026-07-24
- created_by: Sebastien Lambla

## Blockers

- Sequencing only: starts after bloomer v1, in the operator's one-at-a-time
  sidebar-fix series.

## Questions

- Enforcement point: launch script, orchestrator boot self-check, or both —
  and what happens when a second orchestrator for the same repository is
  found (refuse to start, reap the duplicate, or adopt its session)?

## Findings

- Invariant (operator, 2026-07-24): each orchestrator belongs to exactly one
  repository, has exactly one instance, and is always associated with one
  session; that session is always named after the project.
- Feeds [[sidebar-titling]]: project-named sessions are what make the
  faint-repo `/name` rendering coherent in the sidebar.

## Proposal

(to shape at bloom) The invariant enforced at boot: an orchestrator names its
session after its repository and detects duplicate orchestrator sessions for
the same repository instead of coexisting with them.

## Testing

Live verification: boot an orchestrator → its session carries the project
name in the sidebar; provoke a duplicate → handled per the agreed rule; the
operator confirms.
