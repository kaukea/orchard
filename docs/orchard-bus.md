# The orchard bus — messaging specification

Status: **DRAFT for operator correction.** Written 2026-07-27 because the messaging
design existed only as fragments across agent charters, `docs/decisions.md` and the
code, so every session re-derived it and several built against the wrong half. The
operator's spoken specification of 2026-07-27 is the authority for the GRAMMAR; the
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

**[SPEC, changed]** The operator notes pubsub has moved on from the form above; treat
this section as indicative until re-stated.

### Session messages — content in the body

Relaying OPERATOR instructions:

    orchard:operator:message:todo|instructions|request|response|content

Relaying AGENT instructions:

    orchard:agent:message:request|response|content

**[SPEC]** Operator content has its OWN subject family, distinct from agent content.
This is what makes provenance structural rather than a flag someone remembers to set.

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
