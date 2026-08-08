# Testing: inbox-outbox — the boxes and the dispatch

Written for TESTING consumption (operator method, 2026-08-08): the observable
behaviours of scenario 1 and the exact assertions that prove them. Coverage
target: 100% of `tools/boxes.py` and `tools/dispatch.py`, measured with
`coverage`, enforced with `--fail-under=100`.

## Behaviours under test

### The envelope (strict both ways)
- A valid envelope carries exactly `from`, `to`, `subject`, and optionally
  `body`; both addresses are `:session:<dot-free-id>`; the subject is an exact
  member of the closed 22-subject corpus.
- REJECTED on send, each with its own test: a missing required field, any
  unknown field, a non-`:session:` address, a dotted session id, an off-corpus
  subject, a non-string body, a non-dict envelope.

### The outbox
- `put_outbox` validates strictly, writes atomically (`.tmp-` never visible to
  a reader), and names the file `<sender>.<ts>.<uid>.json`.
- The write round-trips: reading the file back yields the envelope.

### The inbox (UDP)
- `receive(sid)` returns only files keyed to `sid`, oldest-first, and DELETES
  each on read — the inbox is empty afterwards, and a second receive returns
  nothing.
- Another session's messages are untouched by my receive.
- An empty inbox returns an empty list.

### The dispatch
- A valid outbox envelope is delivered: it disappears from the outbox and
  appears in the inbox under the RECIPIENT's key, byte-identical body.
- Unreadable JSON and off-schema envelopes are QUARANTINED verbatim — never
  delivered, never deleted silently.
- An empty outbox is a no-op with zero stats; a second run after a full drain
  delivers nothing (idempotence).
- Stats report exactly `delivered` and `quarantined` counts.

### The environment
- `XDG_RUNTIME_DIR` unset is a hard error, not a fallback.
- Box directories are created lazily on first use.

### The agent-communication seam (real CLI)
- One process sends via `boxes.py send`, a second process runs
  `dispatch.py once`, a third receives via `boxes.py receive` — three real
  subprocesses, no shared Python state. The received body equals the sent
  body exactly; exit codes are 0; the sender's CLI refuses an invalid subject
  with a nonzero exit.
- A LARGE body (500k characters) rides stdin (`--body -`), never argv, and
  arrives byte-identical — the transport does not care how the string is
  made.

## How to run

    .venv/bin/python -m coverage run --branch \
        --include='tools/boxes.py,tools/dispatch.py' -m pytest \
        tests/test_boxes.py tests/test_dispatch.py tests/test_boxes_seam.py
    .venv/bin/python -m coverage report --fail-under=100

Every test isolates `XDG_RUNTIME_DIR` in a temporary directory; nothing
touches the live orchard tree.
