- created: 2026-08-08
- created_by: serialseb
- created_during: main

# Courier and messaging: exclusive scope, harvesting the retired branch

## Blockers

None.

## Questions

None recorded yet — the task is unbloomed; the pre-launch bloom round closes the
WHAT before any landscaper is spawned (Decision-050).

## Findings

- The retired observability experiment's branch is preserved at
  `archive/observability` (tip `9a3f914`, 60 commits over `main` at close; see
  `observability.md` → Why cancelled). Its courier-relevant content, surveyed
  2026-08-08 (agent survey, not a ruling on what is kept):
  - `docs/courier-wire.md` — the living wire specification (668 lines, replaces
    `docs/orchard-bus.md`, `[SPEC]`/`[CODE]`/`[GAP]`-tagged per Decision-134).
  - `tools/courier.py` — name registry with NAME addressing, a real topic
    publish/pub-sub path, two session-message relaying families, tolerance for
    retired envelope fields on read, `notify_user` deleted.
  - Test suites: `tests/test_courier_registry.py` (new), `tests/test_courier.py`
    (heavily grown), transport/topic suites.
  - `skills/occasions/` — when to speak, never how (the ruled agent surface).
  - `tools/token-ab.py` — the courier token A/B measurement harness.
  - The branch's own `docs/TODO.md.d/bus-addressing.md` grew ~292 lines of spec
    work there and is NOT on `main` — read it from the tag before redesigning.
- The experiment's failure to answer against: pushing data live to another window
  from a currently executing workflow proved impossible — flawed workflow or
  flawed courier implementation, undetermined (operator, 2026-08-08).
- **Self-wake defect, 2026-08-08.** Operator: *"the courier should never have
  been woken up at all"* — observed: a courier woke on its own parent's status
  telemetry. Under the RULED design this traffic cannot reach a courier at all:
  status is a topic publication whose consumer is a UX (the sidebar), and a
  consumer sees a topic only by SUBSCRIBING — publish and monitor
  (Decision-130), topic membership set up by the supervisor (Decision-133). A
  courier's watch surface is exactly mail addressed to its parent plus its
  subscriptions; it is never a status subscriber. The defect is that main has
  no real topic layer: `post status` writes into the shared project mailbox
  directory (`_monitor_sources()` watches only that directory), so
  publications land where mail is watched. The archived branch built the
  missing layer, verified in its implementation 2026-08-08: its
  `orchard_topic.py` posts to a dedicated `orchard/topics/` root (not the
  mailbox directory); `subscribe` creates `orchard/topics/<name>/<sid>/` and
  publish fans copies into currently-subscribed folders ONLY (an empty topic
  delivers to nobody, by design); the monitor adds only subscribed topic
  folders as extra watch sources. Core salvage: `93f44f5` "Make the topic
  publish path real, and wire up pub/sub" plus the subscribe/fan-out and topic
  storage around it. This is a design-level gap on main, not a monitor filter
  to sharpen.

## Proposal

Operator, 2026-08-08 (verbatim): *"We are going to create a new task focused
exclusively on courier and messaging, and we will be taking the good from the
abandoned branch."*

Scope is the courier and messaging ONLY — no sidebar, no lifecycle-close
choreography, no windowing manager, no question broker (those remain their own
board tasks). First act of the build: harvest from `archive/observability` the
pieces worth keeping, as the operator gates them — not a wholesale merge of the
branch.

## Testing

Not yet agreed — set with the operator at the pre-launch bloom.
