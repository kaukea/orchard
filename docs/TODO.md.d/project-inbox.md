- created: 2026-08-08
- created_by: serialseb
- created_during: f/courier-messaging

# Project inbox

## Blockers

None.

## Questions

All three RESOLVED by the operator's 2026-08-08 messaging-is-not-storage
ruling (Proposal below): persistence — a message never persists; the project
inbox's permanent nature is handled by waking the gardener on receipt for
immediate ingestion; sensitive content is safe because messages are
temporary and deleted on receipt; there is no deletion trigger to define.

## Findings

Carried from `cross-repo-inbox.md` (gh#5, folded 2026-08-08 — read it for
the full record):

- Origin: 2026-07-17 boundary violation — with no channel, a gardener wrote
  a task directly into kauk's tree. Board edges are single-board by
  construction, so cross-repo dependencies survive only as prose.
- HANDOVER is NOT the precedent (operator, 2026-07-17): different lifecycle
  — the inbox is peer-to-peer, durable, and exists to CREATE work.
- FIXED rulings (2026-07-17): sensitive content is ENCRYPTED AND KEPT, never
  delete-and-sanitized — it is the input to the work. Storage direction: a
  dedicated ref namespace `refs/sensitive/<id>` (never notes, never a
  number); DELETION IS THE POINT — `update-ref -d` + reflog expire + gc
  --prune=now, verified to truly remove objects.
- MEASURED LEAK (2026-07-17): a plain local-path `git clone` copies the
  whole object store — refs/sensitive objects LEAK, recoverable via fsck.
  kauk clones local paths today (`bin/kauk:237`): kauk must clone
  `--no-local`/`file://` before refs/sensitive is safe — a kauk-board item
  when this design lands.
- Message kinds worth distinguishing early: requirement · knowledge · ack.

## Proposal

**Ruled, 2026-08-08 (operator):** working in one project, you conceive
tasks or changes for ANOTHER project — possibly offline — or hold documents
that do not belong in your repository (the forensics TOOLING repo vs the
CASES repo carrying actual data). Today agents write the other project's
TODO directly, copying the style they find — making the orchestrator's life
awful. The PROJECT INBOX replaces that: a place to send a message, a file,
or a TASK to a project, for the GARDENER to ingest when it is ready — in
real time if the project is running, or when the project is next started in
a new Claude instance. Arriving items are cleaned up and sorted by the
gardener; a foreign agent never writes the target board.

Build-order position: not yet assigned.

**Ruled, 2026-08-08 (operator):** we do not store anything in git [reading
of dictated "Target"] any more — that has been removed and should never
have been done. Sensitive content lives in TEMPORARY messaging. Should a
message require permanence — don't make it a message; a message is not
permanent by default. The one permanent-natured case is the PROJECT INBOX:
the dispatching component knows that nature and solves it by WAKING THE
GARDENER ON RECEIPT for immediate processing into the durable homes (board,
sidecars). Everything else is XDG and the system survives not getting
messages. Messaging is not storage: a message is DELETED AS SOON AS IT IS
RECEIVED — think UDP. OUT OF SCOPE: ACK, retry, and (for now) encryption or
other suggestions we have no use for.

**Supersession:** this kills the 2026-07-17 rulings carried from the
cross-repo-inbox fold — "sensitive content is ENCRYPTED AND KEPT" and the
`refs/sensitive/<id>` storage direction are struck; the leak measurements
remain as history only. Content that must survive does so as BOARD content
after gardener ingestion, never as a stored message.

## Testing

Bound by the parent's testing doctrine (`courier-messaging.md` §Testing, operator ruling 2026-08-08): unit tested to death, including the unit-test seam for an agent communicating with its counterparty; the scenario does not close without its tests written and run green.
