- created: 2026-08-08
- created_by: serialseb
- created_during: f/courier-messaging

# Agent-to-agent: session-based directed messaging only

## Blockers

Ordering (operator, 2026-08-08): inbox-outbox is built first.

## Questions

None open.

## Findings

- Four-corner comparison done 2026-08-08 (see parent sidecar): branch deletes
  `signal`/`notify_user`/`operator_origin` (main still carries all three, and
  `signal`'s prefix handling is proven buggy); branch adds strict-on-write,
  tolerant-on-read for retired envelope fields; branch suites include the
  real-CLI seam pattern.

## Proposal

Scoped by the operator, 2026-08-08: session-based directed messaging ONLY —
send/request/reply over `:session:` addresses. Agent-NAME addressing lives
in `tree-messaging.md` (clarified 2026-08-08); priorities are not in this
scenario.

**Ruled, 2026-08-08 (operator):** everything goes through the same path. The
message goes to the sender's OUTBOX; a dispatch courier picks it up from the
outbox and dispatches it to the correct location — the INBOX of the
destination session ID. The sender does not need to know how to route; it
needs only the session ID it is sending to. That is the point of the design.
This CHANGES the branch spec: its directed-delivery sections (sender writes
straight into the recipient's mailbox, `orchard_send` §1/§3) are rewritten
onto the boxes model in this scenario.

**Ruled, 2026-08-08 (operator):** request/response is BLOCKING, by
definition: an agent posts a request and waits for the reply before
continuing — no action until the response comes back. Questions to the
operator block for the same reason. Under the boxes model the wait watches
the requester's own inbox for the matching reply.

**Ruled, 2026-08-08 (operator):** an ASK is simply a request/response with a
specific format, defined by SPECIFICATION and never by the agent. This
scenario delivers only that unspecialized blocking transport; the ask's
design (format, presentation, broker behaviour) is folded into
`operator-interacting.md` (gh#219).

**Ruled, 2026-08-08 (operator):** subjects are DECOUPLED from addressing —
the subject names the kind of content (variable detail, e.g. a topic name,
rides in the body); the address (a session, a pubsub topic, your parent) is
where it goes; any subject can travel to any address. The subject families
therefore belong to ALL message-sending scenarios — the whole bus — not to
this one. This scenario builds only the `:session:` address path, carrying
whatever subject rides it. Family definitions live in `fixed-subjects.md`.

## Testing

Bound by the parent's testing doctrine (`courier-messaging.md` §Testing, operator ruling 2026-08-08): unit tested to death, including the unit-test seam for an agent communicating with its counterparty; the scenario does not close without its tests written and run green.
