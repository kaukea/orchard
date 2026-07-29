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

**[CODE]** `cmd_signal` normalises the parent id and sends to
`:session:<parent>`, deliberately stripping a `:session:` prefix first — a caller
that passes a full address would otherwise produce `:session::session:<id>` and leak
a `:` into the delivered filename. That bug is already fixed; do not reintroduce it
by "helpfully" prefixing.

### Cross-project

**[CODE]** A session may address a session in ANOTHER project. `ORCHID_PARENT_SESSION`
names the target session and `ORCHID_PARENT_PROJECT` names the target project slug.
Cross-project delivery is allowlist-gated exactly like any other `:session:` send;
the allowlist is a JSON array of project slugs read from the user's config
(`sidebar-registry.json` — a misnomer retained for now: it is the courier
cross-project allowlist, not a sidebar file).

**[CODE]** With no parent known, a signal is NOT delivered and says so
(`signal <state> — no parent known, not delivered`). Silence here is by design, not
a failure.

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
marked `[GAP]` above for deletion) is NOT hooked into this — only the GLOBAL
`orchard:agent:lifecycle:stopped` subject drives removal, matching "what drives the
sidebar" elsewhere in this document.

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

**[GAP]** `courier.py signal` still carries a parallel invented state list
(`started · building · testing · done · finished · blocked · abandoned`) that appears
in no specification. Ruled 2026-07-29: DELETED, no shim — every caller migrates to
status/lifecycle/outcome in the same change.

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

**[GAP]** The topic PUBLISH path is broken at this commit: `orchard_topic.py:106`
calls `courier.write_orchard_file()` and `courier.orchard_message_name()`, neither of
which exists — any `:topic:` post raises `AttributeError`. (The PROJECT-feed path via
`orchard_deliver()` works and carries all current traffic.) `subscribe`/`unsubscribe`
are not implemented as subjects.

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

**[GAP]** Neither relaying family is built; no priority classes, no outbox flusher.

### The ask — ordinary request/response, defined here (ruled 2026-07-29)

**[SPEC]** Asking the OPERATOR is a request like any other: a directed request to the
reserved `operator` mailbox; the question broker picks it up, displays it, and
returns the response. The operator is a recipient like any other — no special class,
sender, or bespoke path. SUCCEEDED/FAILED are the OUTCOME family, not an interrupt
class; no interrupt vocabulary exists.

**[CODE]** `cmd_ask` (`tools/courier.py:677`) sends
`orchard:agent:message:request` to `:session:operator` with a JSON body
(`question_id`, `question`, `options`) and blocks on the matching `in_reply_to`.

**[GAP]** Nothing drains that mailbox in a live fleet: the broker
(`tools/orchard-question-broker.py`, tested) is deployed nowhere, so every ask hangs.
Deployment is scoped to the `question-broker-dead` task, not this branch.

---

## 2b. Telemetry — the four metrics, attached by the script

**[SPEC, ruled 2026-07-29]** The metrics are **time · tokens in and out · context
remaining · model and effort**. They are detected and attached by the SCRIPT, with no
model involved and at negligible cost (Decision-130): status, identity and telemetry
are answered inside the script, never leaving it, at zero tokens.

**[CODE]** `orchard_topic.py` already attaches an identity snapshot (`agent`,
`feature`, `feature_name`, `task`, `task_name`, `parent`) and a status snapshot
(`model`, `context_tokens`, `spend`) to every post (`_attach_snapshot`).

**[GAP]** Not yet attached: effort, tokens split in/out, timings beyond file
timestamps. Time aggregates (a feature's age vs time actually worked, a task's
running time) are computed by deterministic script/renderer code from event
timestamps — never by an agent reasoning over raw data in its context (operator
ruling, 2026-07-28).

**[GAP]** The durable feature marker (Decision-099: one file per (project, feature),
carrying the tasks and their states — what remains when nothing is happening) has a
correct, tested READER and **no writer anywhere**: the writer was dropped by a
squash-merge and never restored. Quiet tasks currently vanish on restart.

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

**[GAP, remaining]** Filtering moved from the watch path to the drain: the project
directory is shared by every session working that feature, so a courier wakes on its
siblings' traffic and discards what is not addressed to it. That is a real wake cost
that grows with the number of agents on one feature, and it is the residue of the
monitor-overlap problem rather than its solution.

**[GAP] `notify_user` is written, validated, and consumed by NOBODY.** Verified across
`tools/`: every reference either sets the flag or polices its legality — which subject
classes may carry it, which lifecycle states allow it, a grammar audit that calls it a
violation on free prose. The only consumer the code names is `sidebar_model.py`
(`courier.py:733`), which is RETIRED. `sidebar.py` never reads it, and says so: the new
event grammar has no `notify_user` signal to distinguish a wait.

The consequence is not cosmetic. Charters describe `signal --state done --notify-user`
as "the operator's SUCCEEDED interrupt" — the summons that tells the operator an agent
is waiting at a gate. It sets a flag on an envelope nothing acts on. So even with
delivery repaired, a waiting agent surfaces to no one. Anything designed around
"notify the operator" today is designed around a mechanism that does not exist.

**[GAP, introduced by the removal]** Orphan detection lost its structural signal.
Nothing removes the shared project directory when one session ends, so a departed
courier no longer leaves an absence anyone can observe; detection now depends entirely
on `hooks/courier-end.sh`'s self-wake landing.

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
5. **`finished` is not a subject.** It survives as a `courier.py signal --state` value
   from an early draft. The close is `lifecycle:stopped` + `outcome:success|fail`.
