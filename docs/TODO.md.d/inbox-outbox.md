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

**Ruled, 2026-08-08 (operator) — transport:** keep it simple, use the
FILESYSTEM. A binary object sent from A to B could take many transports
depending on the platform — noted, and deliberately not worried about now:
the filesystem is the implementation, not a commitment, and no abstraction
is built for it in this feature.

**Ruled, 2026-08-09 (operator, scope round restarted after reboot) — the
courier subagent dies; the DISPATCHER script is the central authority:**

1. There is no courier subagent in the transport, either direction. The
   central point survives as the DISPATCHER — a script, the single authority
   on where messages go and where they leave. No AI anywhere in the
   transport. Scripts are not tokens; the majority of text must be rejected
   before it ever reaches tokens (operator: "I pay. I don't want to pay.").
2. SEND: the agent calls the send script directly. Strict validation and
   filtering happen in the script, before any token is spent. The hook
   guard flips: it stops forbidding direct script calls and instead forbids
   raw box writes — the sanctioned script becomes the only path that works.
   RULED 2026-08-09: no caller ever hand-assembles JSON — the script is a
   real CLI with named parameters, per-parameter descriptions, and a
   `--help` that IS the documentation; the envelope is built by the script
   from those parameters. The interface is reusable outside agents (human,
   cron, other scripts) by design. The messaging skill carries only the
   pointer to the script (embedding the --help text is permitted), never
   the format.
3. RECEIVE: the dispatcher delivers the message TEXT into the recipient
   session's own harness socket (`CLAUDE_CODE_MESSAGING_SOCKET`, verified
   live on this host: a plain script writing to it injects into the running
   session's conversation). Text only, NEVER a filename — file paths handed
   as instructions get ignored (known failure). Reading is harness-enforced:
   the injection wakes the agent with the message in its conversation.
   Sessions publish their socket path at announce; the dispatcher keeps the
   session→socket map.
4. DEAD RECIPIENT: socket gone → the message parks in the inbox,
   recipient-keyed, drained oldest-first at the recipient's next session
   start. Active revival stays in zombie-revival (gh#30), out of scope.
5. PRIORITIZATION of messages is a dispatcher feature for LATER —
   message-delivering (gh#277), designed to slot into the dispatcher.
   Push-vs-park classification belongs THERE and is the OPERATOR's to
   define (ruled 2026-08-09); this feature invents no default classes.
6. MAILBOX MODEL — "for the most part we are modelling a mailbox." Folders
   are the diagnostics; no ledger, no ack machinery in this feature:
   `outbox/` awaiting dispatch · `inbox/` parked for absent recipients ·
   `sent/` file moved here after successful delivery (the proof it went
   out) · `trash/` rejections and off-schema (replaces "quarantine").
   Live delivery = socket inject + file to sent/. Read-confirmation is NOT
   protocol machinery (operator, 2026-08-09, repeated): a sender wanting an
   acknowledgment requests it in the message body — nothing else, now or
   later. Folder retention/rotation: later, the operator's call.
7. The inotify budget stands: watcher instances never scale with agent
   count. In this feature no standing watcher is needed at all — dispatch
   is synchronous on send; the standing monitor question returns only when
   dispatch detaches (later tasks).
8. STORAGE stays in XDG per previous decisions ($XDG_RUNTIME_DIR/orchard/).
   Message persistence across reboots / long-running cross-project delivery
   is ANOTHER FEATURE, not this one.
9. FROM is richer than the session id. The send script stamps it from the
   environment, zero tokens — verified exported on this host (v2.1.226):
   CLAUDE_CODE_SESSION_ID, CLAUDE_CODE_AGENT (the current agent role),
   CLAUDE_PID, CLAUDE_EFFORT, CLAUDE_CODE_CHILD_SESSION,
   CLAUDE_CODE_ENTRYPOINT, harness version, own MESSAGING_SOCKET; repo
   derivable from cwd. NOT exported (known gaps, not blockers): the model,
   the human --name; parent-session only where the fleet injects
   ORCHID_PARENT_SESSION. Which stamped fields join the envelope is build
   detail; hand-assembly stays forbidden per ruling 2.

*Agent inference, marked (NOT a ruling):* retiring the courier's
announce/listen model touches session-messaging and bus-addressing — the
per-session courier sidecar, its announce protocol, and the courier-only
transport guard are dismantled there, not in this feature. This feature
builds the dispatcher model; the courier keeps running the old model until
session-messaging replaces it.

**Ruled, 2026-08-09 (operator) — the courier's successor is a SKILL:** what
remains of the courier on the AI side is knowledge only (preformat, call
the script, react to injected text) — that becomes a `messaging` skill,
frontmatter-flagged for eager load at session start (precedent:
agent-behaviour), in EVERY component's boot set — every single component
messages. Executed in session-messaging/bus-addressing, not this feature.

## Testing

Bound by the parent's testing doctrine (`courier-messaging.md` §Testing, operator ruling 2026-08-08): unit tested to death, including the unit-test seam for an agent communicating with its counterparty; the scenario does not close without its tests written and run green.
