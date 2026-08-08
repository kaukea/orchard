- created: 2026-08-08
- created_by: serialseb
- created_during: main

# Courier and messaging: exclusive scope, harvesting the retired branch

## Blockers

None.

## Questions

None open.

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
- **Self-wake observed on main, 2026-08-08.** Operator: *"the courier should
  never have been woken up at all"* — a courier woke on its own parent's status
  telemetry. Cause: main lacks the topic layer, so `post status` lands in the
  watched mailbox directory. The specification and the working implementation
  both live in the archive — `docs/courier-wire.md` §2 PubSub and commit
  `93f44f5` with its subscribe/fan-out surroundings (under
  `archive/observability`). Nothing to design here; bringing that back IS this
  feature.

## Proposal

Operator, 2026-08-08 (verbatim): *"We are going to create a new task focused
exclusively on courier and messaging, and we will be taking the good from the
abandoned branch."*

Scope is the courier and messaging ONLY — no sidebar, no lifecycle-close
choreography, no windowing manager, no question broker (those remain their own
board tasks). First act of the build: harvest from `archive/observability` the
pieces worth keeping, as the operator gates them — not a wholesale merge of the
branch.

**Operator, 2026-08-08:** *"the specification in the abandoned branch will
probably be the working base for this"* — `docs/courier-wire.md` under
`archive/observability`, the living SPEC/CODE/GAP-tagged document.

### The scenario list — operator, dictated 2026-08-08

*"This should cover the current feature set."* Worked one by one, in the
operator's order; each scenario is its own board task and sidecar (the sole
home of its rulings and detail):

1. [inbox-outbox](inbox-outbox.md) — ruled first
2. [session-messaging](session-messaging.md)
3. [tree-messaging](tree-messaging.md)
4. [project-broadcast](project-broadcast.md)
5. [pubsub](pubsub.md)
6. [token-sacrifice](token-sacrifice.md)
7. [decoupling-documentation](decoupling-documentation.md)
8. [technical-messages](technical-messages.md)
9. [message-schema](message-schema.md)
10. [fixed-subjects](fixed-subjects.md)
11. [script-defenses](script-defenses.md)
12. [project-inbox](project-inbox.md) — added 2026-08-08, build position unassigned

**Operator, 2026-08-08:** *"I do not mind losing messages in the meantime
while we rebuild."* No transition compatibility is owed during this feature:
scenarios may break live delivery until their successors land; no bridging
machinery is built for the interim. Strengthened same day: all new messages,
all new formats, all new enforcement — NO compatibility with previous
attempts anywhere, under any circumstance (`message-schema.md`).

**Ruled, 2026-08-08 (operator) — hand-up is BY FILE REFERENCE:** the
courier passes content to the parent's context as a file reference, never by
reading it, relaying it, and turning it into language — the parent is
entirely capable of reading the file itself. This is the first and biggest
payment saving: the body is paid for once, parent-side, only when the parent
chooses to read it. DELIBERATE CHANGE to the working-base spec: it
supersedes archived courier-wire.md §6's "a wake carries the parsed
message, not a filename" (that rule optimized turns; this one optimizes
tokens, and the 2026-08-08 measurements back it). Interplay: the courier
still reads what it must validate (script-defenses) — it just never
re-speaks it.

**Ruled, 2026-08-08 (operator) — the hand-up envelope:** the courier hands
up TITLE, IMPORTANCE/PRIORITY, ORIGINATOR and the FILE PATH — the agent is
capable of reading the file itself. The read directive is a CLOSED
vocabulary: `must read` or `should read` — nothing else is accepted. A
message with NO BODY (operator-confirmed reading) is handed up
immediately, whole — its envelope is the message. Never the full text
content. Enforcement of actual reading is a future task
(`read-enforcing.md`).

**Work item, ruled 2026-08-08 (operator) — the invented-language review:**
as part of this feature, review the hallucination that led the courier agent
definition to invent its own language — getting agents to talk to it in
terms completely different from the standardized, originally-requested ones.
Every term in the charter is checked against the ruled vocabulary; invented
terms are removed, which also shrinks the agent file. Prior evidence: the
`signal` verb's seven-state list that appeared in no specification (deleted
on the branch), the invented-verb finding (branch commit 48d6ac5), and
Decision-124 (agents resist change to what they use; enforce mechanically).

**Per-scenario method (operator, same dictation):** compare the code in the
dead branch (`archive/observability`) against the code in main, and the
specification in both branches; extend the specification if needed; possibly
one document per feature, written for TESTING consumption, not agent
consumption. Tests for every single one of these features, per the Testing
section below.

## Testing

**Operator ruling, 2026-08-08 (verbatim):** *"We're going to take it from the
top, and I want everything unit tested to death. including finding a way to
unit test an agent communicating with whatever it is communicating with. Those
will be part of every single scenario I'm going to give you now."*

Binding on every scenario of this feature: unit tests are part of the
scenario's specification — including a unit-test seam for an agent
communicating with its counterparty. No scenario closes without its tests
written and run green.
