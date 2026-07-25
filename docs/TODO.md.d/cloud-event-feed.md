- created: 2026-07-21
- created_by: Sebastien Lambla

## Blockers

- The fleet-sidebar initial run (gh#23) must land first: this task is its first
  follow-up and integrates with the sidebar that run delivers.

## Questions

- Which component owns the event subscription and the file-writing — the orchard
  console, the sidebar process itself, or a separate watcher? The operator scoped
  the writing to happen while the console is running.
- What happens to events raised while the console is not running: replayed on next
  start, or dropped?
- Which events are in scope: all GitHub Actions run/job/step events across the
  fleet's repositories, or only those from the cloud-architect flow's build agents?

## Findings

## Proposal

The fleet sidebar receives all its live updates from courier broadcast messages, which
works locally. The experimental cloud agents cannot reach the local courier, so their
activity would be invisible to the sidebar. This task bridges that gap: subscribe
to the dynamic events that build agents trigger in GitHub Actions and, while the
console is running, write them as files so they integrate transparently with the
sidebar — cloud jobs appear alongside local ones with no special-casing on the
sidebar side.

Constraints:

- Transparency is the point: the sidebar keeps consuming the same shapes it gets
  from the local courier; the bridge adapts cloud events into those shapes.
- Builds on whatever update vocabulary the fleet-sidebar initial run establishes.
- Cloud agents stay operator-gated (Decision-042); this task observes their runs,
  it never launches them.

## Testing

Not yet agreed — to be settled with the operator before launch (WHAT-bar).
Candidate: live-fire — run a cloud build while the sidebar is up and see its
events appear in the sidebar alongside local jobs.
