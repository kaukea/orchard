# The courier wire — messaging specification

Status: **LIVING DOCUMENT (Decision-134).** Kept in sync with the code in the
SAME commit that changes the wire. It is named the COURIER (Decision-131).
Rewritten 2026-08-08 for the courier rebuild: the previous edition (readable
at `archive/observability:docs/courier-wire.md`) described the implementation
that failed five times; per the operator's zero-compatibility ruling nothing
of that model survives here except the grammar he dictated. Where the old
edition is superseded, this document says so explicitly (§7).

Every claim is tagged:

- **[SPEC]** — the operator's stated design.
- **[CODE]** — verified against the implementation, with the file named.
- **[GAP]** — specified but not yet implemented, or spec and code disagree.

---

## 1. The model: boxes and the dispatch

**[SPEC]** Every courier has exactly one INBOX — the sole location in which it
receives ALL message types — and one OUTBOX, where it puts ALL outgoing
message types. A sender never writes into another courier's storage; it knows
only the destination session id. The DELIVERY DISPATCH is the component that
moves messages from outboxes to inboxes — one-to-one, one-to-many, routed,
broadcast: every delivery shape is the dispatch's, never the courier's.
Messages are self-descriptive, which is what lets one outbox serve every
shape.

**[SPEC]** Boxes are LOGICAL, not per-agent folders: common places holding
messages that get filtered, with multiple agents served by the SAME monitor.
Watcher instances never scale with agent count (measured 2026-08-08: 128
inotify instances per user on the host, 50 already in use; watches are
plentiful at 131k — instances are the scarce resource).

**[SPEC]** MESSAGING IS NOT STORAGE — think UDP. A message is deleted as soon
as it is received. Nothing is ever stored in `.git/`. Permanence is never a
message property: what must survive becomes board content via ingestion (the
project inbox wakes the gardener on receipt). ACK, retry and encryption are
OUT OF SCOPE. Message loss during the rebuild is accepted; no transition
compatibility is owed to any previous format.

**[SPEC]** Transport is the FILESYSTEM, kept simple. A binary object could
ride other transports per platform — noted and deliberately not designed for.

**[CODE]** `tools/boxes.py` — the box primitives and their CLI:

    $XDG_RUNTIME_DIR/orchard/boxes/outbox/      <sender-sid>.<ts>.<uid>.json
    $XDG_RUNTIME_DIR/orchard/boxes/inbox/       <recipient-sid>.<ts>.<uid>.json
    $XDG_RUNTIME_DIR/orchard/boxes/quarantine/  off-schema files, moved verbatim

Outbox filenames are SENDER-keyed (the dispatch routes off the envelope);
inbox filenames are RECIPIENT-keyed (the kernel can filter at the watch).
Writes are atomic (`.tmp-` prefix, then rename); readers never see partials.
`receive` drains the caller's own inbox files oldest-first and DELETES on
read. Large bodies ride stdin (`--body -`), never argv — the transport does
not care how the string is made.

**[CODE]** `tools/dispatch.py` — the delivery dispatch, first incarnation:
`dispatch_once()` drains the common outbox oldest-first; a valid envelope is
atomically renamed into the inbox under the recipient's key (the move is both
the delivery and the outbox deletion); an unreadable or off-schema file is
moved verbatim to quarantine. One-to-one only in this scenario.

**[GAP]** One-to-many, routed and broadcast shapes; the topic (pub/sub) layer
with its crawler and garbage collector; the shared monitor over the inbox;
the project inbox and its gardener wake.

---

## 2. Addresses

**[SPEC]** Sender is always a session: `From: :session:<session-id>`.
Session ids are dot-free — that is what makes `<sid>.<ts>.<uid>.json` split
unambiguously, and it is load-bearing.

**[SPEC]** Address forms, by scenario:

| Form | Meaning | State |
|---|---|---|
| `:session:<id>` | one specific session | **[CODE]** `boxes.py` validates; dispatch delivers one-to-one |
| topic (name TBD at build) | pub/sub over a subscription register | **[GAP]** — pubsub scenario; the topic holds messages while the crawler copies to current subscribers' inboxes; a message clears when all current subscribers have it; an empty, inactive topic is garbage collected |
| ancestor (parent → root) | any agent on the sender's path to the root, resolved from inherited identity — the agent never handles an ancestor's session id | **[GAP]** — tree-messaging scenario; sibling/subtree messaging is explicitly UNDECIDED and must not be assumed |
| agent NAME | resolves against only the names in the sender's own tree | **[GAP]** — tree-messaging scenario; topic names and agent names are different names with nothing to do with one another |

**[SPEC]** There is no broadcast-to-everyone. Project-level broadcast is
project-level pub/sub: the project topic opens with the project and closes
with it. **[GAP]** — project-broadcast scenario, requires subscription
filtering first.

---

## 3. The envelope and the subjects

**[CODE]** The envelope is STRICT BOTH WAYS (`tools/boxes.py`): exactly
`from`, `to`, `subject`, optional string `body`; any deviation — unknown
field, malformed address, off-corpus subject, non-string body — is rejected
on send and quarantined on dispatch. Zero tolerance, no legacy fields, no
shims. A message that fails validation on READ means something bypassed the
sanctioned path: potentially a security event (§6).

**[SPEC]** Subjects are a TREE of nouns naming the kind of message; each leaf
inherits the root's properties. Subjects are DECOUPLED from addresses: any
subject can travel to any address; variable detail (a topic name, a
delegation id) rides in the body, never the subject.

**[CODE]** The corpus is the closed 22-subject set (Decision-092), matched by
exact membership in `boxes.SUBJECTS` — the operator's base under review at
build, very likely unchanged:

    orchard:agent:{status, outcome:success|fail,
                   lifecycle:starting|started|stopping|stopped,
                   delegation:schedule|begin|end,
                   message:request|response|content}
    orchard:bus:{subscribe, unsubscribe}
    orchard:operator:message:{todo, instructions, request, response, content}
    orchard:task:outcome:{completed, failed}

**[SPEC]** The four channels stay apart: lifecycle (four states exactly) ·
status (freetext, one word, for a UX) · outcome (`success|fail`, the contract
other tools consume) · requests. Asking and waiting are status, never
lifecycle states. Operator content has its own subject family — provenance is
structural, never a flag.

**[SPEC]** SYSTEM messages — the purely technical family: anything the script
can receive and answer without breaching the AI boundary (identity, status,
uptime, ping) is handled script-to-script at zero tokens. **[GAP]** — the
family's subjects join the corpus in the system-messages scenario.

---

## 4. Delivery semantics

**[SPEC]** Request/response is BLOCKING by definition: an agent posts a
request and takes no action until the response comes back; the wait watches
the requester's own inbox. Questions to the operator block the same way and
are ordinary requests — the ask is simply a request/response with a specific
format defined by SPECIFICATION, never by the agent. **[GAP]** — the blocking
verbs arrive with session-messaging; the ask's format lives in
`operator-interacting`.

**[SPEC]** The courier hands up BY FILE REFERENCE: title, importance or
priority, originator, the file path, and a read directive from a CLOSED
vocabulary — `must read` or `should read`, nothing else. A message with no
body is handed up whole; the full text is never re-spoken into the parent.
(Deliberate supersession of the old wake-carries-the-parsed-message rule:
that optimized turns; this optimizes tokens, and the 2026-08-08 measurements
back it.) **[GAP]** — courier surface, session-messaging scenario;
enforcement that a must-read was actually read is the `read-enforcing` task.

**[SPEC]** The courier is capped at 25k tokens of context: at the cap it
tells its parent to launch a successor and exits — announcing shutdown
through the status system, declaring once the time it needs, finishing its
in-flight blocking waits while new arrivals wait in the inbox for the
successor. Never a silent disappearance. **[GAP]** — token-sacrifice
scenario.

---

## 5. What is actually expensive

**[SPEC]** Script-side processing is FREE; waking an agent and spending its
tokens on a message it did not care about is the only real cost. Measured
2026-08-08: a subagent's harness floor is 18,285 tokens before its charter
says a word; each courier wake replays the whole transcript. Consequences:

- The courier runs under its OWN SETTINGS FILE allowlisting only what it
  needs — no unwanted skills, no project instruction files, no room to go
  wild. **[GAP]** — token-sacrifice scenario; floor re-measured at build.
- Filtering is filename-first at the kernel where possible (recipient-keyed
  inbox names), envelope-level in the script otherwise. Exactness matters
  only at what the script HANDS UP.
- Watcher instances are scarce (§1) — shared monitors, never per-agent or
  per-filter watcher fleets. (Deliberate supersession of the old
  one-watcher-per-filter rule: processes were free, instances are not.)

---

## 6. Defenses

**[SPEC]** Messaging can reach the inside from the outside; it is defended
accordingly. Anything not coming from a script vetted by the current script
is a danger — usable for exfiltration or induced token burn. The script
rejects ANY deviation: file location, file format, content length, missing
fields, possibly a process allowlist. Bypassing the courier has historically
been NORMAL behavior, so the defense treats a bypass attempt as the expected
case. **[CODE]** — first layer only: strict validation + quarantine
(`tools/boxes.py`, `tools/dispatch.py`).

**[SPEC]** The body is formalized (not free text only) and validated twice:
STRUCTURAL by the script, LOGICAL by the courier — does the free text match
the intent of the message, judged from a seed set of examples that grows or
shrinks with experience. The breach response has three levels: QUESTIONABLE
(the user is asked: does this look right to you?), WARNING (the message is
ignored, loudly), ERROR (stops the current process altogether). Quarantine
is forensics, not the response. **[GAP]** — script-defenses scenario.

---

## 7. Superseded from the previous edition

Recorded so nobody rebuilds against the failed model:

| Old rule (archive edition) | Fate |
|---|---|
| Sender writes directly into the recipient's project-dir mailbox (`orchard_send`, §1/§3) | DEAD — everything flows outbox → dispatch → inbox |
| Storage at `orchard/projects/<repo>.<project>/` with `<sid>.marker` heartbeats | DYING — replaced by the boxes layout at the courier cutover; `tools/courier.py` still runs the old model until session-messaging replaces it |
| Wake carries the parsed message, not a filename (§6) | SUPERSEDED — hand-up is by file reference (§4) |
| One watcher per (directory, pattern) pair; extra processes cost nothing (§6) | SUPERSEDED — instances are scarce; monitors are shared (§5) |
| Per-topic per-subscriber folders (`orchard/topics/<name>/<sid>/`) | SUPERSEDED — the topic is a holding place plus a subscription register; delivery lands in ordinary inboxes (§2) |
| `notify_user`, `operator_origin`, the `signal` verb and its invented state list | DEAD — deleted on the branch, never returning; provenance is structural |
| Priority classes (`immediate`/`wait-a-round`/`batch`), outbox flusher | PARKED in gh#277 (message-delivering) — not part of this rebuild |
| Messages archived to zip after 120 minutes | DEAD — messaging is not storage |
| `tools/message.schema.json` (old envelope) | DYING — becomes the single schema definition of THIS wire at the session-messaging cutover **[GAP]** |
