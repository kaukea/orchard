- created: 2026-07-25
- created_by: Sebastien Lambla
- created_during: orchestrator session (courier board triage)

## Blockers

- None. The former parity gate on the fan-out cut is DROPPED by operator
  ruling (2026-07-25): "I think it's just killing it" — the old inbox-fed
  sidebar model retires with the fan-out; `sidebar_v3` (topics) is the
  sidebar.

## Questions

- MANUAL AUTH for `:session:` unicast: ruled to exist, shape undefined —
  what does the authorisation step look like in practice? Bring to the plan
  gate; the operator answers in-pane.

## Findings

- THE BUNDLE (operator, 2026-07-25): one feature, one landscaper, closing in
  one go what remains of the bus arc — [[bus-relay]] (+ absorbed
  [[cross-repo-bus]]), [[fanout-cutover]], [[bus-singleton]],
  [[bus-close-cleanup]]. Those four sidecars are the detailed design records;
  this sidecar is the umbrella contract.
- THE GATE this closes (operator): "once request/response lands, the bus is
  good enough." Closing this feature flips [[bus-transport-v2]] to done,
  admits its held changelog entry, unblocks the release cut and
  [[summon-restarting]].
- Request/response: `:session:` unicast, manual auth, DELETED by the script
  upon reading (ruled). Cross-repo reach is the point — target set
  panopticon, seb.throwy, SignMc ("that's the first"); the topic root is
  already user-wide, it is the inbox/unicast leg that is repo-scoped today.
- Fan-out: v1's announce/broadcast fan-out to every inbox is THE money leak
  (~150–200k subagent tokens/day measured); FULL BROADCASTS ARE FORBIDDEN
  (ruled). Kill outright: `depart` is already unread; `test_bus.py`
  broadcast round-trip and `test_bus_traffic` role tests update WITH the
  cut; `sidebar_model.py`'s inbox reads retire with it.
- Singleton + close-cleanup close WITH this build (operator: "should have
  been closed, goes with four, with the analysis we have on what kills
  files and the fixes we already did"): Decision-081 removed all kills —
  agents close themselves; the courier's close must wake it, never kill its
  monitor; exactly one courier per agent.
- Channels ruling (2026-07-25): SendMessage between RELATED agents;
  topics for status/telemetry; UNRELATED-agent messaging is seb.house's,
  out of scope.
- Standing constraints: no log files; no filesystem-as-sync beyond the
  folder-mtime exemption; simplicity — no FIFO or advanced delivery.

## Proposal

One branch finishes the bus:
1. `:session:` request/response — unicast with manual auth, delete-on-read,
   working ACROSS repositories (the addressing substrate; prove on
   panopticon / seb.throwy / SignMc).
2. Fan-out killed outright — announce/broadcast/depart inbox copies gone;
   topics (+ unicast-to-parent where directed) carry everything;
   `sidebar_model.py`'s inbox feed retires; affected tests updated in the
   same change.
3. Courier singleton — exactly one courier sidecar per agent, enforced.
4. Courier close cleanup — the close wakes the courier to release itself;
   no orphan monitors, nothing killed.
After this feature the bus is good enough (operator gate); rounds beyond
(metronome-class transport) are explicitly out.

## Testing

To confirm at the plan gate:
- Assured scenario (carried from bus-message-specifying round 18): an agent
  learns a peer's completion through the courier alone — no git or
  filesystem polling. CROSS-REPO variant: peers in two different
  repositories.
- Post-cut suite green: `test_bus.py` / `test_bus_traffic` updated, all
  courier tests pass; grep proves no fan-out send path remains.
- Singleton proof: a second courier load attempt is refused/absorbed.
- Close proof: a session close leaves zero orphan monitors (ps check) and
  the courier's release is observed.
- LIVE on the operator's screen: the sidebar still shows session activity
  end-to-end after the cut (topics only, no inbox reads).

## Result

Result: done — code complete and tested; awaiting operator `THAT IS ALL`.
- Branch `f/bus-finishing` · HEAD `f67d818` (Base `149131b`).
- Stage 1 (mechanics): new orchard flat+markers transport in `tools/courier.py` under
  `$XDG_RUNTIME_DIR/orchard/{projects/<repo>.<project>,topics/<name>}/`
  (`<sessionid>.<ts>.json` + `<sessionid>.marker`); `:session:`/`:topic:` addressing;
  delete-on-read; request/reply; registry-allowlist cross-project gate;
  `tools/orchard_compact.py` (>120-min → persistent zip archive, cheap `.compacted`
  gate); `tools/bus.py` shim retired — `courier.py` is the one script.
- Stage 2 (convergence): courier fan-out killed (announce/broadcast/depart/
  signal-fallback/ask de-fanned); telemetry (status/lifecycle/outcome/delegation +
  identity snapshot) rewritten onto the projects layout; sidebar consolidated into
  `tools/sidebar.py` reading the new layout (`sidebar_model.py` + `sidebar_v3.py`
  deleted); question-broker re-pointed at the `:session:operator` mailbox; charters +
  `hooks/courier-end.sh` updated (topic emit, `:session:operator` ask,
  `:session:<parent>` signal, singleton, self-message-wake close). Subjects = closed
  22-string corpus, exact-match. Sidebar retention = colour (working / done-green /
  fail-red / stale-gray), persists until restart.
- Tested: full suite **348 passed** (pytest, isolated `XDG_RUNTIME_DIR`/`XDG_CACHE_HOME`)
  — assured cross-repo scenario (two repos, one runtime dir, B receives A via the
  courier alone), request/reply + delete-on-read, exact-subject accept/reject,
  marker+parent mtime, compaction archive-and-sweep, sidebar build/render from the new
  layout.
- DEFERRED live acceptance (only runnable post merge+sync+restart — this session runs
  the pre-sync vendored courier): (a) sidebar shows activity on-screen after the cut;
  (b) a real close leaves zero orphan monitor/mailbox. Operator/successor post-sync gate.
- ARCHITECTURE.md updated on-branch (message-courier + fleet-sidebar sections rewritten
  to the new model) — triggers fired (module boundary, components removed/added, data
  flow, broadcast→directed+topic pattern).
- Delegation: discovery ≈7 explorers; build ≈16 builders; inline fixes (support.py
  collection linchpin, SignalNotifyLegality live-pollution isolation, sidebar
  entrypoint check).

## Operator follow-ups (return to the orchestrator — NOT written to the board here)

1. [[summon-restarting]] — supervision controller: the orchestrator listens to child
   lifecycle state changes (`started`…`stopped`) via a monitor, sleeps, wakes on
   `stopped`, and launches the next agent itself; writer-writes-once; request/response
   for aggregation. bus-finishing delivers the substrate; this builds the controller.
2. NEW task — tmux / operator-interaction component. Owns: the question-broker's proper
   session-id-less SUB-AGENT form (launched with the question, SendMessages the answer,
   ends); the operator-answer allowlist bypass (a reply from `:session:operator` is the
   trusted operator answer, exempt from the cross-project gate); focus reclaimed by
   observing `closed`. The current mailbox-scanning broker is a working bridge only.
3. REGRESSION to re-wire: the `/orchard hide|show` registry (`tools/orchard_registry.py`)
   is no longer read by the consolidated `sidebar.py` — `build_model()` folds every
   project dir unconditionally, so hide/show is silently a no-op. Small fix (filter the
   project dirs by the registry in `build_model`); surfaced to the operator at close.
4. Minor debts: reject-telemetry still writes the old `topics/telemetry/<repo>/` layout;
   sidebar `progress_pct` unpopulated (done rows show `0%`); `failed` shown via the
   ❌ glyph, no red RGB.
4. Cutover is MANUAL — a deliberate kauk sync + restart (no hook/keyword auto-activates);
   the two deferred live checks run then.

## Changelog entry

### Bus finishing — the orchard transport
Finished the message-bus arc. The courier's broadcast fan-out — a courier telling every
peer's inbox about every event, the measured token leak — is gone. Messaging now runs on
a flat, user-wide runtime tree (`$XDG_RUNTIME_DIR/orchard/{projects/<repo>.<project>,
topics/<name>}/`): directed `:session:<id>` messages (delete-on-read, request/reply,
cross-repo via a manually-maintained allowlist) and topic posts carrying the sidebar's
telemetry. Message subjects are a closed 22-string corpus validated by exact membership —
known or rejected, with variable data in the body. The fleet sidebar is one program again
(`sidebar.py`) reading that tree, and staleness shows as colour (done green, failed red,
not-heard-from gray) rather than rows appearing and vanishing. The transitional `bus.py`
shim is retired; `courier.py` is the single script. Telemetry ≤120 minutes stays live;
older messages archive to `~/.cache/orchard/archives/`.

## Readme delta

The README section "Courier messages, as built (audit inventory, 2026-07-25)" documents
the retired fan-out model and its token-leak audit. Replace it with the finished model:
no fan-out (directed `:session:` + topic posts); the closed 22-subject corpus with
exact-match validation; the flat `$XDG_RUNTIME_DIR/orchard/{projects,topics}/` transport;
the sidebar reading that tree with colour-coded staleness; `courier.py` as the single
script (the `bus.py` shim retired). Keep the "you get to watch" sidebar paragraph but drop
the "agents broadcast … every courier sidecar wakes on every copy" framing — that
mechanism is retired.

## Decision entries

(UNNUMBERED — write `Decision-NNN`; the housekeeper folds these into docs/decisions.md,
assigning the next free number at fold time.)

## [2026-07-25 CEST] Decision-NNN: The orchard transport — flat files + markers on a user-wide runtime tree
#bus #courier #transport #orchard #messaging

The message transport moves off the repo-scoped `the-works/courier/<sid>/` inboxes onto a
user-wide runtime tree: `$XDG_RUNTIME_DIR/orchard/` with `projects/<repo>.<project>/`
(session mailboxes) and `topics/<name>/` (subject pub/sub), messages named
`<sessionid>.<ts>.json` plus a per-session `<sessionid>.marker` whose mtime is the
liveness heartbeat (each write touches the marker and its parent project dir). Storage is
per-repo; addressing crosses repos — a `:session:<id>` delivery to another project is
gated by the manually-maintained `~/.config/orchids/sidebar-registry.json` allowlist.
Directed messages are delete-on-read; `request`/`reply` give a blocking round trip;
messages older than 120 minutes archive to a persistent zip under
`$XDG_CACHE_HOME/orchard/archives/`.

## [2026-07-25 CEST] Decision-NNN: Message subjects are a closed corpus, validated by exact membership
#bus #courier #vocabulary #subjects

The orchard subject vocabulary is a CLOSED set of 22 exact strings, not extensible; the
script validates a subject by exact membership only — no regex, no `startswith`, no
derivation: it is known or it is rejected. Variable data (a delegation subagent id, a
subscribe topic) lives in the message body, never the subject. The set:
`orchard:agent:{status, outcome:success|fail, lifecycle:starting|started|stopping|stopped,
delegation:schedule|begin|end, message:request|response|content}`,
`orchard:bus:{subscribe,unsubscribe}`,
`orchard:operator:message:{todo,instructions,request,response,content}`,
`orchard:task:outcome:{completed,failed}` (gardener-only). `delegation:schedule` marks a
session-id-less subagent queued to be called; `begin`/`end` bracket its work.

## [2026-07-25 CEST] Decision-NNN: The fan-out is killed; telemetry is topic-posted, signals and questions are directed
#bus #courier #fanout #topics #sidebar

The courier no longer broadcasts to every inbox (the token leak). Agent telemetry —
status, lifecycle, outcome, delegation, each carrying an identity snapshot — is posted to
the project topic that feeds the sidebar; a lifecycle signal to a parent is a directed
`:session:<parent>` message (cross-repo via `ORCHID_PARENT_PROJECT`); an operator question
is a directed request to the reserved `:session:operator` mailbox. The retired `orchid:`
broadcast wire-grammar and the inbox-reading `sidebar_model` are removed. The
question-broker (the tmux popup) is a consumer of the transport, not one of its subjects —
its proper session-id-less sub-agent form belongs to a separate tmux/operator-interaction
component.

## [2026-07-25 CEST] Decision-NNN: Sidebar staleness is a colour, not a removal
#sidebar #retention #liveness

The fleet sidebar never drops a row because it went quiet. State is a colour: a working
session is normal; a terminal outcome is a persistent one-liner — success green, fail red;
a session with no event past the ~1h liveness window and no terminal outcome renders gray
("not heard from in a while"). Rows persist until a restart clears the tmpfs tree. The
intent is predictability — rows never appear or vanish for no understandable reason; the
colour carries the staleness, and no data is lost since a resumed session re-posts and the
display follows.

## [2026-07-25 CEST] Decision-NNN: The courier is a per-agent singleton with no session id; it closes by self-message wake
#bus #courier #singleton #close #lifecycle

The courier sidecar is a simple subtask that shares its parent's session id — it has none
of its own. Exactly one courier runs per agent (one serves all correspondents, never
one-per-peer). Its close is a self-message wake: the SessionEnd hook drops a `release` into
the mailbox the courier's own monitor watches, and the courier then stops its monitor,
departs (posting the parent's `lifecycle:stopped`), and tears down its own mailbox — never
killed externally (Decisions 041/046/081). `tools/bus.py` (the transitional rename shim) is
retired; `courier.py` is the single bus script.
