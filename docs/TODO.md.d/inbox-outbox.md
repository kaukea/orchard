- created: 2026-08-08
- created_by: serialseb
- created_during: f/courier-messaging

# Inbox, outbox, delivery dispatch: the courier's two boxes

## Blockers

None.

## Questions

None open.

## Findings

- Neither specification defines inbox/outbox as first-class objects: main has
  no outbox concept at all; the archived branch has `orchard/outbox/` only as
  batch-priority machinery (lockfile-singleton flusher) plus `wait-a-round/`
  parking. Send writes directly into recipient storage in both — which the
  ruling below forbids. This scenario EXTENDS the spec.

## Proposal

**Ruled, 2026-08-08 (operator, confirmed reformulation):** the INBOX is the
sole location in which a courier receives ALL message types; the OUTBOX is the
location a courier puts ALL outgoing message types — a courier never writes
into another courier's storage. The DELIVERY DISPATCH is a new component
(exists nowhere yet) that pushes messages from the sender's outbox to the
recipient inbox(es) — one-to-one, one-to-many, routed, broadcast: every
delivery shape is the dispatch's, never the courier's. Scheduled delivery and
the priority classes stay in gh#277 (message-delivering), a later follow-up —
one thing at a time.

Draft build plan (agent proposal, NOT yet operator-approved): restore
`docs/courier-wire.md` from the archive as working base and add the
boxes-and-dispatch section ([SPEC]/[GAP]); testing-consumption doc; outbox
write path; inbox as sole receiving surface; `tools/delivery_dispatch.py`
one-to-one only, synchronous on send, structured to detach later; unit suites
plus the real-CLI seam test.

**Ruled, 2026-08-08 (operator) — boxes are LOGICAL, monitors are SHARED:**
having an inbox and an outbox does NOT mean independent folders per agent.
They are common places to put messages, filtered — with multiple agents
served by the SAME monitor. Measured on this machine the same day: inotify
allows 128 instances per user (50 already in use; watches are plentiful at
131k), so watcher instances must never scale with agent count — five
projects x twenty agents with per-agent watchers bursts the limit. This
supersedes archived courier-wire.md §6's "one watcher per
(directory, pattern) pair — extra processes cost nothing": they cost
instances, and instances are the scarce resource.

## Testing

Bound by the parent's testing doctrine (`courier-messaging.md` §Testing, operator ruling 2026-08-08): unit tested to death, including the unit-test seam for an agent communicating with its counterparty; the scenario does not close without its tests written and run green.
