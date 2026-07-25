- created: 2026-07-24
- created_by: Sebastien Lambla

## Blockers

- Sequencing only: starts after bloomer v1, in the operator's one-at-a-time
  sidebar-fix series.

## Questions

- Enforcement point: launch script, gardener boot self-check, or both —
  and what happens when a second gardener for the same repository is
  found (refuse to start, reap the duplicate, or adopt its session)?

## Findings

- Invariant (operator, 2026-07-24): each gardener belongs to exactly one
  repository, has exactly one instance, and is always associated with one
  session; that session is always named after the project.
- Feeds [[sidebar-titling]]: project-named sessions are what make the
  faint-repo `/name` rendering coherent in the sidebar.
- Naming slice pulled forward (2026-07-24 evening): the rename-sessions-
  after-their-repo half ships in the sidebar-titling one-go quick pass; this
  task retains the single-instance / duplicate-handling enforcement.

## Proposal

(to shape at bloom) The invariant enforced at boot: a gardener names its
session after its repository and detects duplicate gardener sessions for
the same repository instead of coexisting with them.

## Testing

Live verification: boot a gardener → its session carries the project
name in the sidebar; provoke a duplicate → handled per the agreed rule; the
operator confirms.
