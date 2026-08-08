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
