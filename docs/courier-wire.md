# The courier wire — messaging specification

Status: **LIVING DOCUMENT (Decision-134).** Kept in sync with the code in the SAME
commit that changes the wire; never a snapshot from a design round. It is named the
COURIER (Decision-131). First written 2026-07-27 because the messaging design existed
only as fragments across agent charters, `docs/decisions.md` and the code, so every
session re-derived it and several built against the wrong half. The operator's spoken
specification of 2026-07-27 is the authority for the GRAMMAR, extended by his rulings
of 2026-07-29 (recorded in `docs/TODO.md.d/observability.md` and folded in below); the
code is the authority for CURRENT BEHAVIOUR. Where they differ this document says so
rather than picking a winner.

Every claim below is tagged:

- **[SPEC]** — the operator's stated design.
- **[CODE]** — verified by reading `tools/courier.py` / `tools/orchard_topic.py`.
- **[GAP]** — spec and code disagree, or the design is stated but unbuilt.

---

## 1. Addresses

**[SPEC]** Sender is always a session:

    From:  :session:<session-id>

Recipients:

| Address | Meaning | Gate |
|---|---|---|
| `:session:<session-id>` | one specific session | requires manual auth |
| `:topic:<topic-name>` | a fixed list of topics | needs daemon signature |

**[SPEC]** There is no broadcast-to-everyone. Fan-out was removed deliberately;
a message is directed at one session, or published to a named topic.

**The two are different in kind, and are filtered differently.**

| | `:session:<id>` | `:topic:<name>` |
|---|---|---|
| what it is | a response, or incoming mail | a NOTIFICATION |
| who it is addressed to | one specific session | usually NOBODY — `to` is not meaningful |
| what a subscriber gets | only what is addressed to it | EVERYTHING published on that topic |
| how it is filtered | by FILENAME — the recipient id is in the name, so the kernel can do it at the watch | by SUBJECT — which lives inside the envelope, so only after reading |

You rarely want everything a topic carries, so subject filtering is the whole point of
subscribing to one. And because the subject is inside the file, that filtering is
necessarily post-parse — which costs nothing (§6). **Never filter a topic by `to`**: a
notification is addressed to no one, and the session id in a topic path is the
PUBLISHER's, not a recipient's.

**[CODE]** Who the filename is keyed by, verified in `orchard_send()` — this is what the
whole filtering scheme rests on:

- directed (`kind == "session"`): `file_sid = value`, the **recipient**. True for ANY
  directed message, not only a reply — an unsolicited message to you still lands as
  `<your-sid>.<ts>.json`, which is why a filename filter catches it.
- topic (`kind == "topic"`): `file_sid = sender`, the **publisher**. Independent
  confirmation that filename filtering is meaningless for topics: it would select on who
  published, not on what you wanted.

**[CODE]** Session ids are validated `dot_free=True`. That is the only reason
`<sid>.<ts>.json` can be split unambiguously on its first dot, and it is load-bearing:
allow a dot into a session id and every name in the tree becomes ambiguous.

**[CODE, removed 2026-07-29]** `cmd_signal` used to normalise the parent id by
building `f":session:{to}"` unconditionally — which, contrary to what this section
used to claim, did NOT strip an existing `:session:` prefix first, so a caller
passing an already-prefixed address doubled it (`:session::session:<id>`), leaking a
`:` into the delivered filename. `cmd_signal` and this whole wrapping step are gone
(§2's "Agent status tracking" [GAP], now resolved) — every remaining `--to` in
`courier.py` (`send`/`request`/`reply`) takes a full `:session:<id>`/`:topic:<name>`
address directly from the caller, with no bare-id convenience wrapping and so no
doubling to reintroduce.

### Cross-project

**[CODE]** A session may address a session in ANOTHER project via
`send`/`request`/`reply --to :session:<id> --target-project SLUG` (an explicit flag,
not env-var-driven). Cross-project delivery is allowlist-gated
(`_authorize_cross_project`); the allowlist is a JSON array of project slugs read
from the user's config (`sidebar-registry.json` — a misnomer retained for now: it is
the courier cross-project allowlist, not a sidebar file).

**[RESOLVED, A1]** `ORCHID_PARENT_PROJECT` was, until `cmd_signal`'s deletion, read ONLY
by `cmd_signal` (as the implicit `--target-project` for a parent-directed signal with no
parent known otherwise) — now that `cmd_signal` is gone, nothing in `courier.py` reads
it at all; only `ORCHID_PARENT_SESSION` is still read (`identity_of()`'s
`parent_session` display field, unrelated to addressing). Grepped for an orphaned
setter across the tree (`tools/bloomer-launch.sh` was the suspected one): none exists —
`tools/bloomer-launch.sh` sets `ORCHID_PARENT_SESSION` only and never set
`ORCHID_PARENT_PROJECT`, so there was nothing to remove. No directed parent callback
remains anywhere in the surface: a landscaper's close is a `lifecycle:stopped` +
`outcome` event the SUPERVISOR listens for (Decision-129's owner-listens shape), never
a signal addressed at a remembered parent.

### Addressing by NAME — ruled 2026-07-29

**[SPEC]** The address an agent uses is the agent's NAME; `:session:<id>` addressing
STAYS alongside it (cross-repository was named as one case where it is used; the
division of labour between the two forms is deliberately unsettled). The SCRIPT mints
stable identifiers and owns filesystem location, access and dispatch (Decision-130);
resolution is never the agent's problem and never appears in an agent definition.

**[SPEC]** The script maintains a name → identifier/mailbox REGISTRY. An agent enters
it when its courier initialises; **when agents go down they disappear from the list**
— the courier removes the entry when `lifecycle:stopped` lands (Decision-129: the
component that created the entry listens for the finish and destroys it).

**[SPEC]** Resolution is NEAREST-FIRST (Decision-132): a name resolves in your own
tree first; failing that, walk up until only main has one, and deliver there.
Outside your own tree an agent may ONLY ask questions or query status — enforced by
the script, not by prose. OPEN, not to be assumed by an implementer: whether
teammates sharing a topic gain rights across a tree boundary that non-teammates do
not.

**[SPEC]** Two live agents holding the same name at the same level is EXPECTED team
behaviour (Decision-121: several agents share one logical destination) — a
name-addressed send is delivered to EVERY live holder. A name whose every holder has
`stopped` is an ERROR back to the sender: undeliverable, nobody live by that name.

**[CODE]** Built in `tools/courier.py` (this commit). One atomic JSON file per
session under `$XDG_RUNTIME_DIR/orchard/registry/<session-id>.json`
(`name_registry_dir`/`name_registry_path`), holding `name`, `session_id`,
`project_slug`, `mailbox_dir`, `started_ts`. Written/refreshed by `register_agent_name`
— called from `cmd_init`, and refreshed again (mtime bump, `_touch_agent_name`) on
every `orchard_send()` a session makes, so an active session stays live between
`init` calls without a full re-register. `name` is this session's agent role
(`CLAUDE_CODE_AGENT`, i.e. `identity_of()["agent_type"]`) — the only per-agent
identity fact the codebase already establishes that several concurrent sessions
legitimately share (Decision-121). **Not itself a separate ruling** — nothing else in
the tree defines a distinct "name" concept, so this is the implementer's choice for
this step, flagged for confirmation rather than asserted as settled design.

**[CODE]** Removal on death: `orchard_deliver()` (the single funnel every current
lifecycle post already uses — both `orchard_send()`'s session/topic delivery and
`orchard_topic.py`'s `do_post`) calls `_deregister_on_stop()`, which removes the
**sender's own** entry the moment its `orchard:agent:lifecycle:stopped` envelope
passes through — never another session's entry (Decision-129, "never delete a live
peer's entry"). `cmd_signal`'s separate, older lifecycle encoding
(`orchard:agent:message:content` body `{"kind":"lifecycle",...}`, the 7-state list
resolved above by deletion) was never hooked into this — only the GLOBAL
`orchard:agent:lifecycle:stopped` subject drives removal, matching "what drives the
sidebar" elsewhere in this document. Now that `cmd_signal` is gone entirely, this is
moot rather than merely unhooked: nothing emits that body shape any more.

**[CODE]** Stale-guard: `live_name_registry_entries()` treats a registry file's own
mtime as its liveness marker and excludes anything older than
`NAME_REGISTRY_STALE_SECONDS` (3600s, matching `sidebar_model.ACTIVE_WINDOW_SECONDS`'s
"still counts as alive" convention — not imported, so `courier.py` carries no
dependency on the sidebar layer). This is what catches a session that died without
ever emitting `lifecycle:stopped` (a crash): its file is left behind, but a `resolve`
skips it once stale.

**[CODE]** `resolve_name(name)` (`tools/courier.py`) implements nearest-first exactly
as three tiers, scoped to the sender's OWN REPO only:

1. the sender's exact `project_slug()` (this worktree);
2. any other worktree of the same repo (same `<owner>.<repo>` prefix, any branch
   except `main`);
3. the repo's `main` branch.

Every live holder at the NEAREST non-empty tier is returned (same-level clash
fan-out, Decision-121) — `send --to <name>` delivers to each of them and reports the
count. A name held by nobody live, in any tier, is `courier: undeliverable: nobody
live named '<name>'` (nonzero exit). **Cross-repo name resolution is NOT
implemented** — `resolve_name` never searches another repo's registry; this stays
OPEN per the spec above.

**[CODE]** Outside-tree enforcement: when the resolved tier is not the sender's own
project, `send --to <name>` requires `--subject orchard:agent:message:request`
(covers both "ask a question" and a status query riding the same request subject);
any other subject is refused in the send path with an explicit "outside your own
tree" error (Decision-132), never merely documented.

**[CODE]** `send --to <name>` (no colon prefix) is the name form; `:session:<id>` and
`:topic:<name>` are unchanged and still route through `orchard_send()` directly. A
name-resolved delivery bypasses `orchard_send()`'s cross-**repo** allowlist gate
(`_authorize_cross_project`) on purpose: `resolve_name()` only ever searches the
sender's own repo, so a resolved candidate is never actually cross-repo — that
allowlist exists for `ORCHID_PARENT_PROJECT`'s genuinely-different-repo case.

**[GAP, unchanged]** Whether a teammate sharing a topic gains rights across a tree
boundary that a non-teammate does not (Decision-133's open question) remains
unimplemented and unassumed by the above.

---

## 2. The fixed message list

**[SPEC]** The subject vocabulary is CLOSED and matched EXACTLY. Validation is
absolute: an off-list subject is rejected, not coerced. This is what lets tooling
written later, by someone else, interoperate without coordinating with the sender.

### Agent status tracking — PROJECT scope

    orchard:agent:status                     freetext, ONE word describing the activity
    orchard:agent:outcome:success|fail

**[SPEC]** The outcome messages are the CONTRACT — they are what other tools consume.
Emit them faithfully; never overload or approximate a body to suit a local need.

**[SPEC, ruled 2026-07-29]** Four channels, kept apart: **lifecycle** (four states,
below) · **status** (freetext, one word, for a UX — `blocked` and `waiting` are
status) · **outcome** (`success|fail`) · **requests** (questions, the operator
included). Asking a question and waiting are NORMAL lifecycle — started and not
stopping — never states.

**[CODE, resolved 2026-07-29]** `courier.py signal` and its parallel invented state
list (`started · building · testing · done · finished · blocked · abandoned`,
`LIFECYCLE_STATES`) are DELETED outright, no shim: `cmd_signal`, its argparse wiring,
`SIGNAL_NOTIFY_STATES`, and the `{"kind": "lifecycle", ...}` body shape (and the
`validate` audit code that only ever checked that shape) are gone from
`tools/courier.py`. No caller in this repo invoked `courier.py signal` outside its own
tests and doc comments — the verb was fully dead weight (docs/TODO.md.d/observability.md
step C2). `orchard_topic.py`'s own `LIFECYCLE_STATES` (the correct four-state
`starting|started|stopping|stopped`, §2's "Agent lifecycle tracking") is untouched and
unaffected — it was never the same constant, only confusingly named the same. Two test
classes exercising the deleted verb (`SignalAttributionTests`,
`SignalNotifyLegalityCliTests` in `tests/test_courier.py`; `SignalPrefixTests` in
`tests/test_orchard_transport.py`) are removed rather than migrated: their entire
premise — a `signal` CLI verb with `--to` prefix-doubling and cross-project
parent-attribution behaviour — no longer exists to test. Agent charter prose
(`agents/*.md`) mentioning `signal` still describes the old vocabulary; that rewrite is
a later step (A1), not done here.

### Agent lifecycle tracking — GLOBAL (drives the sidebar)

    orchard:agent:lifecycle:starting|started|stopping|stopped

**[SPEC]** `stopping` = cleaning up · `stopped` = done.
**[CODE]** `orchard_topic.py` documents exactly this and enforces
`LIFECYCLE_STATES = ("starting", "started", "stopping", "stopped")`.

### Subagent delegation — GLOBAL

    orchard:agent:delegation:begin:<subagentName|session-id>
    orchard:agent:delegation:end:<subagentName|session-id>

### PubSub — GLOBAL

    orchard:bus:subscribe:<topic-name>       script creates the agent's folder and monitor
    orchard:bus:unsubscribe:<topic-name>     script deletes it, discarding remaining content

**[SPEC, restated 2026-07-29 — Decision-133]** A team may span several worktrees with
a teammate in each; the mechanism is pub/sub: subscribe to a topic FOR THE CURRENT
FEATURE OR TASK, then talk freely to everyone working on it, depending on how the
SUPERVISOR set it up. The topic is the address — which is how the cross-subtree case
is served without the subtree ever becoming an identifier. Owning which topic exists
and who is on it is the supervisor's duty.

**NOTE, unresolved naming:** the subject literals above carry `bus`, which
Decision-131 retires everywhere — but these exact strings are the operator's own
dictated grammar of 2026-07-27. Renaming a wire constant he dictated needs his word;
flagged, not assumed.

**[CODE, fixed 2026-07-29]** `courier.write_orchard_file()` and
`courier.orchard_message_name()` now exist — the canonical `<sid>.<ts>.json` namer and
the atomic write every orchard file goes through, validated against Decision-091's
closed filename shape set (`validate_orchard_filename`, raises rather than repairing a
malformed name) before anything touches disk. `orchard_deliver()` is refactored onto
these two rather than duplicating the write; `orchard_topic.py`'s `write_message()`
(its telemetry-rejection path, the concrete site that raised `AttributeError`) now
resolves. (The PROJECT-feed path via `orchard_deliver()` is unaffected — same
behaviour, now sharing the same underlying primitive.)

**[CODE, built 2026-07-29]** `subscribe --topic <name>` / `unsubscribe --topic <name>`
are real CLI verbs (script-owned, per Decision-130 — not routed through `send`'s
envelope machinery, since creating/removing a folder is a structural action, not a
delivery). `subscribe` creates `orchard/topics/<name>/<sessionid>/`, the shape
`_monitor_sources()`'s own comment anticipated before this was built; `unsubscribe`
`rmtree`s it, discarding whatever was still queued, exactly as specified. A `:topic:`
publish now fans a COPY into every folder that currently exists under the topic
(`_topic_subscriber_dirs`) rather than writing one shared bulletin-board file — no
subscribers means the publish reaches nobody, consistent with "no delivery guarantee."
`monitor` folds one `MonitorSource` per currently-subscribed topic in alongside the
own-mailbox source, so a courier wakes on topic traffic the same way it wakes on
direct mail.

### Session messages — content in the body

Relaying OPERATOR instructions:

    orchard:operator:message:todo|instructions|request|response|content

Relaying AGENT instructions:

    orchard:agent:message:request|response|content

**[SPEC]** Operator content has its OWN subject family, distinct from agent content.
This is what makes provenance structural rather than a flag someone remembers to set.

**[SPEC, ruled 2026-07-29 — consumption on receipt]** The operator family is
AUTHORITY + IMMEDIATE: it wakes the recipient at once and is handed up AS the
operator speaking — structural provenance replaces the `operator_origin` flag, and
relayed gate words count as the operator's own. The agent family is ordinary directed
mail, with a PRIORITY class as an optimisation: `immediate` (sent at once) ·
`wait-a-round` · `batch`. Batched traffic is written by ONE outbox-flusher script on
a 5-second cadence; immediate traffic never queues.

**[CODE, built 2026-07-29]** Both subject families were already members of
`ORCHARD_VALID_SUBJECTS`; this commit builds the behaviour on top. Provenance:
`is_operator_authority(subject)` (`tools/courier.py`) is true for the operator family —
`operator_origin` is deleted outright (envelope field, `make_envelope`/
`make_orchard_envelope` kwarg, `--operator-origin` CLI flag, schema property); every
writer and the one flag-shaped reader (`sidebar_model.py`, already retired) are gone or
migrated to the subject check. `send --to ... --subject orchard:operator:message:*` now
refuses any `--priority` other than `immediate` outright — the family cannot queue.

**[VERIFIED, transition note, 2026-07-29]** A courier still on `main` keeps sending
`operator_origin` until this branch lands fleet-wide, so a mailbox this branch reads
can still receive a message carrying it. Strict-on-write, tolerant-on-read already
holds without any change: `_schema_violation()` (the `additionalProperties: false`
rejection) runs only when THIS session builds and sends its own envelope
(`orchard_send()` / `_deliver_to_registry_entry()`); the receive path
(`orchard_receive_own()`) only `json.loads()`s a stored envelope and hands it back —
it never runs schema validation against what it consumes, so a legacy field rides
through unrejected (`RetiredEnvelopePropertyToleranceTests`). This tolerance covers
retired ENVELOPE properties only — subject vocabulary stays closed and strictly
validated on every path, write or read.

Priority: `send --priority immediate|wait-a-round|batch` (default `immediate`), legal
only on `orchard:agent:message:*` — any other subject rejects a non-immediate value.
`immediate` writes straight through the unchanged `orchard_deliver()` path. `batch`
queues into `$XDG_RUNTIME_DIR/orchard/outbox/` (one JSON file per pending delivery:
`{dir, sid, envelope}`) and lazily starts the flusher (`courier.py flush-outbox`,
spawned by `_ensure_flusher_running`) — a lockfile-singleton (`orchard/outbox.
flusher.lock`, `flock` exclusive-non-blocking, no PID/staleness logic: a losing
duplicate just exits) that drains the outbox every 5 seconds and closes itself the
first time a drain finds nothing left (Decision-129's owner-closes shape applied to a
queue rather than a registry entry).

**[CODE, resolved 2026-07-29 — "wait-a-round delivers on the recipient's next wake",
`docs/TODO.md.d/bus-addressing.md` §Decision entries]** `wait-a-round` is now
DISTINCT from `batch` at delivery, not a second name for the same queue.
`deliver_with_priority` writes it straight through `orchard_deliver()` — at once, like
`immediate` — but with `message_dir` pointed at `WAIT_A_ROUND_DIRNAME`
(`<project-dir>/wait-a-round/`), a subfolder of the recipient's own project directory
that the recipient's own mailbox `Monitor` never scans: `inotifywait` is armed on the
project directory itself, not recursively (`-r` is never passed), so a file landing in
a child directory of it raises no `create`/`moved_to` event there at all — the message
is fully delivered, only its ARRIVAL wakes nobody. `orchard_receive_own()` — the
function every ordinary drain (`monitor`'s own wake, a plain `receive`) already goes
through — now reads `WAIT_A_ROUND_DIRNAME` alongside the direct mailbox
(`_own_mailbox_message_files`, sorted together by filename so a mix of the two still
reads oldest-first), so a parked message surfaces the next time the recipient wakes
for ANY other reason, exactly as ruled. Proven both ways in `tests/test_courier.py`
(`MonitorCliTests.test_wait_a_round_message_alone_wakes_nobody`/
`test_wait_a_round_message_is_delivered_on_the_next_ordinary_wake`, plus the
lower-level `PriorityQueueingTests` pair). The "handed up AS the operator speaking"
consumption behaviour (relayed gate words counting as the operator's own) is a
courier-AGENT prompt/consumption concern, not a wire-level one — it is not built here;
agent charter prose describing it is a later step (A1), per this branch's own scoping
in the "Agent status tracking" section above.

### The ask — ordinary request/response, defined here (ruled 2026-07-29)

**[SPEC]** Asking the OPERATOR is a request like any other: a directed request to the
reserved `operator` mailbox; the question broker picks it up, displays it, and
returns the response. The operator is a recipient like any other — no special class,
sender, or bespoke path. SUCCEEDED/FAILED are the OUTCOME family, not an interrupt
class; no interrupt vocabulary exists.

**[CODE]** `cmd_ask` (`tools/courier.py:677`) sends
`orchard:agent:message:request` to `:session:operator` with a JSON body
(`question_id`, `question`, `options`) and blocks on the matching `in_reply_to`.

**[GAP]** No persistent deployment drains that mailbox: the broker
(`tools/orchard-question-broker.py`, tested) runs only when started by hand — the
operator corrects the earlier "deployed nowhere, every ask hangs" absolute: it "was
used several times. It wasnt used all the time" (2026-07-29). While it is down, an
ask blocks forever. Keeping it running all the time is scoped to the
`question-broker-dead` task — operator, 2026-07-29: "it is a part of native terminal
feature (which also includes the windowing system)" — not this branch.

---

## 2b. Telemetry — the four metrics, attached by the script

**[SPEC, ruled 2026-07-29]** The metrics are **time · tokens in and out · context
remaining · model and effort**. They are detected and attached by the SCRIPT, with no
model involved and at negligible cost (Decision-130): status, identity and telemetry
are answered inside the script, never leaving it, at zero tokens.

**[CODE, corrected 2026-07-29]** `orchard_topic.py` attaches an identity snapshot
(`agent`, `feature`, `feature_name`, `task`, `task_name`, `parent`) and a status
snapshot to every post (`_attach_snapshot`). The status snapshot carries `model`,
`context_tokens`, `spend` (the full four-class breakdown — `input_tokens`,
`output_tokens`, `cache_read_input_tokens`, `cache_creation_input_tokens`, all
already computed by `courier.status_of()`) **and now `tokens_in`/`tokens_out`**,
promoted out of `spend` to first-class fields (`orchard_topic.py:_status()`) — the
renderer reads these two directly rather than reaching into the nested dict for the
two classes it actually charts. The earlier wording of this section ("tokens in/out
not yet attached") was imprecise: `spend` already nested them; only the top-level
promotion was missing, and is now built.

**[CODE, corrected 2026-07-29]** `effort` is now attached via an ordered READER CHAIN,
documented source first, our own fallback last — `courier.status_of()` reads, in
order: **`CLAUDE_EFFORT`** (Claude Code's own DOCUMENTED hooks environment variable —
current effort level, values `low|medium|high|xhigh|max`; source: the Claude Code
hooks reference at code.claude.com) → **`CLAUDE_CODE_REASONING_EFFORT`** (its
documented alias) → **`ORCHID_EFFORT`** (ours — set at our own launch sites as a
fallback for any context the two documented harness variables don't reach). The first
one present wins; `_status()` carries the result through when any of the three is set.
A plain ordered `or`-chain (`os.environ.get("CLAUDE_EFFORT") or os.environ.get(
"CLAUDE_CODE_REASONING_EFFORT") or os.environ.get("ORCHID_EFFORT") or None`) —
deliberately kept simple so a future documented mechanism can be inserted at the HEAD
of the chain without restructuring it. Absent when none of the three is set — no value
is invented (`test_status_snapshot_has_no_effort_when_claude_effort_unset`; the chain's
own priority order is proven by `test_effort_reader_chain_claude_effort_wins_over_the_
other_two`/`test_effort_reader_chain_reasoning_effort_wins_when_claude_effort_absent`/
`test_effort_reader_chain_orchid_effort_is_the_last_resort`, `tests/test_orchard_
topic.py`). **`ORCHID_EFFORT` itself is not yet SET anywhere**: this repo's launch/
dispatch tooling was grepped for a site that constructs a `claude` process invocation
and explicitly chooses an effort value to pass it — `tools/bloomer-launch.sh` is the
only shell script in the tree that spawns a `claude` process at all, and it does not
pass `--effort` or set an effort env var; every other effort "choice" in the codebase
(agent-def frontmatter `effort:` keys, `tools/bloom_engine.py`'s launch-sizing
recommendation) is either read by the harness independently of any script here, or is
advisory text a human/gardener acts on when spawning via the Agent tool — never a
shell invocation this repo's own scripts control. FLAGGED, not fixed here: there is
currently no concrete site to export `ORCHID_EFFORT` at; the fallback exists and is
tested, but has no producer yet.

**[CODE, built 2026-07-29]** `dollars` — spec §3's "tokens and dollars in one line —
tokens tick live, dollars translate them" — is promoted the same way `tokens_in`/
`tokens_out` were: `_status()` now reads `courier.status_of()`'s own `estimates.
cost_usd` (built by `courier.estimates_for()` from the existing per-model
`MODEL_CARD` price table — no new rate invented anywhere in this step) and carries it
through as a first-class `dollars` field. Empty exactly when `estimates` itself is
empty — an unrecognised model — never a guessed figure
(`test_status_snapshot_promotes_dollars_from_estimates`/`test_status_snapshot_has_no_
dollars_for_an_unrecognised_model`, `tests/test_orchard_topic.py`). Consumed by
`sidebar_model._repo_time_and_tokens`, which now returns `(age, worked, tokens,
dollars)` — `dollars` summed across each agent's own latest `status.dollars` figure,
same aggregation convention TOKENS already used, formatted via `sidebar_text.
_format_dollars` (two decimal places, matching the footer mock's `"$7.90"` shape) —
feeding `Repo.dollars`, which the footer formatters (`sidebar_render_text.
footer_lines`/`done_footer_line`) already read duck-typed.

**[RESOLVED]** Timings beyond file timestamps are not needed and none are attached:
every orchard message filename already carries a timestamp (`<sid>.<ts>.json`), and
every feature-marker task entry carries its own `updated` timestamp (§2b below). Time
aggregates (a feature's age vs time actually worked, a task's running time) are
computed from those existing timestamps by deterministic script/renderer code, never
by an agent reasoning over raw data in its context (operator ruling, 2026-07-28) —
attaching a separate duration field at write time would only duplicate what the
timestamps already carry.

**[CODE, resolved 2026-07-29]** The durable feature marker (Decision-099: one file
per (project, feature), carrying the tasks and their states — what remains when
nothing is happening) now has a writer: `courier.write_feature_marker()` merges each
delivered envelope's `identity` block into `<feature-id>.marker` via
`merge_feature_marker()`, called from `orchard_deliver()` for project-mailbox
deliveries only (a topic subscriber delivery carries no durable task record).
Merge-never-truncate: an existing CURRENT-shape (`task`-keyed) entry for a
DIFFERENT task under the same feature survives untouched; anything not in that
shape (a schema-1 entry keyed by the retired `feature` field, a bare delegation
`label`, a `sessions` identity cache) is discarded rather than crashed on
(`_load_feature_marker()`/`merge_feature_marker()` are FAIL-OPEN throughout — a
missing, zero-byte, or malformed marker loads as empty, never raises). Task state
follows the subject: `lifecycle:starting`/`started` → `working`,
`outcome:success`/`fail` → the terminal `done`/`failed` (sticks — nothing after it
moves it back), anything else leaves a known state alone and defaults an unseen task
to `working`. Quiet tasks now survive a restart.

---

## 3. Storage layout

**[CODE, confirmed by operator]** Flat files plus a marker mtime per project:

    ./orchard/topics/<name>/...
    ./orchard/projects/<repo>.<project>/<sessionid>.<ts>.json
    ./orchard/projects/<repo>.<project>/<sessionid>.marker

Messages are flat, named `<sessionid>.<ts>.json`, consumed by globbing
`<sid>.*.json`. Liveness is the `<sessionid>.marker` mtime heartbeat, not a message.

An earlier design used a directory per session
(`.../<sessionid>/<ts>.json`); it was **rejected in favour of flat plus marker**.
Charter text that watches a per-session directory predates that decision.

---

## 4. Who writes, who wakes

### Writing

**[SPEC]** The COURIER is the single writer for its session — no carve-out, not even
for mechanical status ticks (Decision-096 and its addendum). Bypassing the courier to
write the transport directly is architecture-breaking.

**[SPEC]** Couriers belong to SESSION-BEARING agents only. An in-session subagent has
no identity, loads no courier, and writes nothing; it may be handed a delegated
reference to its parent's courier. Note the consequence for guards: a subagent
INHERITS its parent's session id, so session id alone cannot distinguish a parent's
courier from a subagent's.

### Waking

**[CODE, fixed 2026-07-27]** A courier arms its persistent `Monitor` on its own orchard
PROJECT directory, obtained from `courier.py project-dir`. Because the project directory
is now one-per-worktree (§3), that watch only carries traffic from agents working the
same feature.

The defect this replaced, recorded because it cost days: the courier's only persistent
watch used to be armed on the git-directory box (§5), where `:session:` traffic never
landed. The orchard tree WAS watched by `_wait_for_orchard_activity()`, but its only
callers are `_await_orchard_reply()` / `_await_orchard_reply_forever()` — a
request/reply wait. So an UNSOLICITED inbound message woke nothing unless the courier
already happened to be blocking on a reply, and the operator's close gate worked only
when something was coincidentally waiting. It failed silently the rest of the time.

**[CODE, fixed 2026-07-29]** `_wait_for_orchard_activity()` — the watch
`request`/`reply`/`ask` block on — now carries the same `--include` filter `monitor`'s
own mailbox source already used (`_own_mailbox_path_filter(sid)`), so the ONE remaining
unfiltered watch in the codebase is closed: a sibling session's traffic and a marker
heartbeat in the shared project directory no longer raise the kernel event that
re-checks this wait. Per §6 this is a convenience layered on top of the exact
`in_reply_to` match `_find_orchard_reply()` already did — that match was always
correct; this only cuts how often it re-runs, closing the wake-cost gap that grew with
the number of agents on one feature.

**[CODE, resolved 2026-07-29]** `notify_user` is DELETED outright, consequence of the
no-interrupt-class ruling (`docs/TODO.md.d/bus-addressing.md` §Decision entries,
"There is no interrupt class: outcome is outcome, the ask is a request"): the flag
carried no live consumer, only the writers and the policing that guarded it. Removed
from `tools/courier.py`: the envelope-builder kwarg (`make_envelope`,
`make_orchard_envelope`), the `--notify-user` CLI flag, `NOTIFY_FORBIDDEN_ORCHID_CLASSES`
and its two legality checks (`enforce_orchid_grammar`'s send-time reject,
`_orchid_traffic_violation`'s audit-time reject), the grammar-audit clause in
`_free_prose_traffic_flag` that called a free-prose broadcast carrying the flag a
VIOLATION (an undirected broadcast is now uniformly a WARNING, flag or no flag), and
the `message.schema.json` property. `_question_envelope` (legacy, unused by `cmd_ask`
today) no longer sets it either. A waiting agent is STATUS (`"waiting"`, per §2's
four-channel ruling), surfaced by the sidebar like everything else — not a bespoke
summons mechanism.

**[RESOLVED 2026-07-29]** Orphan detection lost its structural signal (no directory
removal to observe on departure), but does NOT depend entirely on
`hooks/courier-end.sh`'s self-wake landing — that was true only while the durable
feature marker had no writer (§2b's now-resolved GAP). Three independent MTIME-based
signals stand in for the removed absence, none of them needing a departure event to
fire at all (they read stillness, not a message):

1. **Per-task staleness, the sidebar's own signal** — `tools/sidebar_model.py`'s
   `_status_for()` reads a feature-marker task's `updated` field (written by
   `courier.write_feature_marker()`/`merge_feature_marker()`, §2b) and flips it to
   `stale` once it ages past `ACTIVE_WINDOW_SECONDS` (60 minutes), checked BEFORE the
   lifecycle/outcome read — a marker still claiming `working` whose `updated` is old
   renders stale regardless (Decision-094/100: staleness is a colour, never a
   removal). This is the row-level orphan signal an operator actually sees, and it
   was starved of data — not broken — while the writer was missing.
2. **Per-session heartbeat** — the `<sid>.marker` touched by every `orchard_deliver()`
   (§3) ages the same way; a session that stops posting simply stops advancing it.
3. **Name-registry stale-guard** — `live_name_registry_entries()` /
   `_is_name_entry_live()` (`NAME_REGISTRY_STALE_SECONDS`, 1 hour) already reads a
   dead registry-entry mtime as not-live "even if `lifecycle:stopped` never arrived
   (a crash)" — independent of both markers above, covering name-resolution
   liveness specifically.

`hooks/courier-end.sh`'s self-wake remains the PROMPT clean path (an orderly
`lifecycle:stopped` removes the name-registry entry at once, §4 "Writing"/`_deregister_on_stop`)
— what changed is that it is no longer the ONLY path: a crash or a silently killed
session still ages out under all three mtime signals above without it.

---

## 5. The removed second channel

**[CODE, removed 2026-07-27]** A second, older channel used to exist alongside the
orchard transport: a per-agent mailbox directory under
`<git-common-dir>/the-works/courier/<agent-id>/`. It is GONE — `send` now accepts
orchard addresses only, `receive` drains only the orchard mailbox, and
`courier_root()` / `inbox()` / `list` / `root` no longer exist. Kept here as the
record of why, because the reasoning generalises.

Its property, stated plainly because it is the reason it was built: `--git-common-dir`
is SHARED BY EVERY WORKTREE of a repo. A worktree holds only a `.git` file pointing
into `<common>/worktrees/<name>`; `the-works/` itself is common. So this box lets
agents in sibling worktrees reach each other through the filesystem with no runtime
directory involved. What it CANNOT do is cross projects — that is the orchard tree's
job. Retiring it therefore means the orchard transport subsumes the same-repo case
too, and the shared-filesystem shortcut is given up deliberately, not by oversight.

**A shared mailbox cannot coexist with worktrees at all.** Worktrees exist so several
jobs run in parallel, so duplicate and concurrent instances are the NORMAL case. A
mailbox living in shared `.git`, keyed by an id that instances can share, is therefore
guaranteed to collide — and to collide destructively, since any holder can delete any
box. Session-id inheritance turns "likely" into "certain": a subagent inherits its
parent's `CLAUDE_CODE_SESSION_ID`, so every subagent of a session resolves to the SAME
box as its parent.

That is not an edge case, it is the design meeting its own premise. It fired on
2026-07-27: a mistakenly spawned second courier ran `teardown` on its way out and
removed a live session's inbox, taking the watcher with it. Any duplicate instance of
any job would do the same.

The orchard runtime tree does not have this property — it is keyed per project and
per session outside the repo, and carries a marker heartbeat rather than a mailbox
whose existence is load-bearing.

- `courier_root()` / `inbox()` build it; `root` is still a CLI subcommand.
- `cmd_send` falls back to it for any non-orchard address.
- `cmd_receive` drains it first, then appends `orchard_receive_own()`.
- `courier.py:972`'s own comment describes the orchard layout as living
  *"alongside the courier_root() layout above"*.

**Per the operator (2026-07-27): this box should no longer exist.** Removing it also
dissolves §4's wake defect, because there is then only one channel to watch. Patching
the Monitor to watch both paths would entrench the thing that is meant to disappear.

Anything built on `inbox()` / `courier_root()` is therefore built on a structure
slated for deletion — including the mailbox-ownership guard added in commit
`54bae0e`, whose singleton protection would need re-siting on the orchard session
identity when the box goes.

---

## 6. What is actually expensive

**[SPEC]** Script-side processing is FREE. Waking an agent and spending its tokens on a
message it did not care about is the only real cost in this system.

Every filtering decision follows from that asymmetry, and it points the opposite way to
normal engineering instinct:

- It is always cheaper to over-read and discard inside `courier.py` than to hand a parent
  one ignorable message. Reading every file in a directory and throwing most away costs
  nothing worth counting.
- Kernel-side filtering (`inotifywait --include`) is a convenience for cutting obvious
  noise — sibling sessions, marker heartbeats — NOT a correctness mechanism. Do not
  contort a regex to achieve perfect selectivity there.
- **One watcher per target/filter list.** `--include` is a single GLOBAL regex for the
  whole invocation, not per-path, so one process watching several targets would have to
  widen to a union pattern and let noise through on all of them. A separate watcher per
  (directory, pattern) pair keeps every filter exact — and since scripts are free, the
  extra processes cost nothing that matters. The corollary is a teardown obligation:
  whatever verifies a watcher is gone must account for several.
- The only boundary that must be exact is what the script HANDS UP. Everything upstream
  of it is free optimisation.
- The same logic makes a wake carry the PARSED MESSAGE rather than a filename: a wake
  that forces the agent to go and look costs a second turn, and turns are the scarce
  thing.

Stated because the instinct to optimise CPU, syscalls or file reads is strong and, here,
optimises the axis that does not matter.

## 7. Rules that fall out of the above

1. **Language stops at the agent it is spoken to.** An agent is responsible for the
   words used with it and takes the decision they call for. An agent that receives
   language, does nothing, and hands it on for another to act on is a bug — the
   responsibility went missing between the two. What crosses a boundary is STRUCTURE.
2. **State is read, never inferred.** If it is `stopped` it is closed; if it is
   `stopping` it is cleaning up. Nothing probes a pane, parses a transcript, or reads
   meaning into silence.
3. **Ending is announced in two events, by every agent**: `lifecycle:stopping` before
   releasing anything, then release in reverse creation order, then `lifecycle:stopped`
   with the outcome as the final act. An agent stuck in `stopping` is a lost handover.
4. **Routing authority is exclusive; subscription is not.** One role decides what runs
   next; any number of components may attach to the stream for telemetry, cleanup or
   issue-pushing. A supervising controller and a distributed fleet are not
   antithetical.
5. **`finished` is not a subject.** It was a `courier.py signal --state` value from an
   early draft; `signal` and that whole invented state list are deleted (§2). The
   close is `lifecycle:stopped` + `outcome:success|fail`.
