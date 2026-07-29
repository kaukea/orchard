- created: 2026-07-29
- created_by: gardener
- created_during: main

# The message bus, implemented to its specification — with the sidebar that consumes it

## SCOPE — OPERATOR RULING 2026-07-29: everything, and this is the last attempt

Operator, verbatim: *"everything, this is the last go before i go to chatgpt. Spec
implemented, testable and tested, token efficient, base for communication, and systematic
displaying of sidebar using the this information so i can manage multiple features and
multiple projects at the same time"*.

Five attempts have not delivered it. The deliverable is all five of these together — not
a transport with the sidebar deferred again:

1. **The specification implemented** — `docs/orchard-bus.md` and the rulings recorded in
   this sidecar, built as stated rather than re-derived.
2. **Testable and tested** — the testing gate is met with real runs, not a green build.
3. **Token efficient** — measured, not asserted. The current cost is ~3,000 tokens per
   message delivered; the charter is 4,023 words re-read by every agent every session.
4. **A base for communication** — something the rest of the fleet builds on, rather than
   a fifth thing that gets rewritten.
5. **The sidebar, systematically displaying this information**, so the operator can manage
   **multiple features and multiple projects at the same time**. This is the application
   the whole design exists to serve: a completely independent program with **no AI in it**,
   showing every project, feature, task, subtask and metric in one pane, in real time.

### The governing principle (operator, same round)

**Delegate the maximum of the functionality to the SCRIPT — to reduce both token cost and
the "creativity" of the models.**

The script was already modified to enforce every rule: **no message that does not respect
the format, or whose subject is unknown, was ever accepted.** Enforcement exists; the
charter then re-explains it in prose to a model, which is the waste.

**Freedom lives in the BODY.** There is a body in messages — that is where an agent
expresses whatever it wants to express. The envelope is closed and enforced; the body is
open. An agent needing to say something unusual says it in the body, and never by
inventing a subject, a verb, or a state.

### THE PRODUCER AND ITS CONSUMERS MOVE TOGETHER — always, no exceptions

Operator, verbatim: *"every time someone tries to change one without taking into account
the other, you ruin a day of my work"*.

The transport and the things that read it are **one change**. A round that alters the
script's output without altering the sidebar that renders it — or alters the sidebar to
expect a shape the script does not emit — costs the operator a day. This has happened
repeatedly and is the most expensive recurring failure on this feature.

Binding consequences for the build:

- **No partial landing.** The script, the agent-def, the skill, the tests and the sidebar
  land together or not at all. There is no "transport first, sidebar next round" — that
  sequencing is precisely what produced five rewrites.
- **This feature is NOT split across parallel workers with separate footprints.** The
  footprints are the same footprint. One coherent change.
- **A change to an emitted shape is a change to every reader of that shape**, and the
  reader is found and updated in the same commit — never left to be discovered by the
  operator when his sidebar goes blank.
- **The test that matters is end to end**: an agent emits, and the sidebar shows it. A
  passing unit test on either side alone does not demonstrate the seam that keeps
  breaking.

### Relaying — wanted, never implemented

Operator: *"We didn't implement relaying but this is also a powerful tool."* The
specification carries it as its own subject families —
`orchard:operator:message:todo|instructions|request|response|content` and
`orchard:agent:message:request|response|content` — with operator content deliberately kept
as a distinct family so provenance is structural rather than a flag someone remembers to
set. It is in scope here.

## Proposal

Operator ruling, 2026-07-29, on reading the cross-worktree wake defect: **there is more
to fix than the parent project, because the supervisor makes "parent" useless.** The
transport addresses messages by a single inherited `parent`, and that model no longer
describes the fleet it runs on.

Two things broke it at once:

- **A supervisor now sits between the gardener and the landscaper** (Decision-075). The
  landscaper's `parent` is its supervisor, the supervisor's `parent` is the gardener —
  so "signal the parent" means something different at each hop, and neither hop can
  address the gardener directly without knowing the topology it was told not to learn.
- **Parallel workers** (Decision-121: a feature is built by a TEAM of landscapers with
  fluid task binding). Several agents share one logical destination, and one agent may
  need to reach a sibling rather than an ancestor. A single-slot `parent` cannot express
  either.

This task settles what an agent addresses instead. It is the design question underneath
the live defect — the immediate `ORCHID_PARENT_PROJECT` breakage is separate and fixed
first (see Blockers).

## Blockers

- The LIVE defect is fixed ahead of this task, not inside it: `orchard_send`
  (`tools/courier.py:1130`) computes `target_project = ORCHID_PARENT_PROJECT or
  project_slug()`, and `ORCHID_PARENT_PROJECT` is unset, so a child in a feature worktree
  writes its close signal into its OWN per-branch orchard directory while its parent
  watches another. Diagnosed on `f/transport-test-reconciling`, recorded in that sidecar.
  That is a defect with a known small fix; THIS task is the model that replaces the
  concept once the bleeding stops.

## OPERATOR RULING 2026-07-29 — address by AGENT NAME, and the work lives in the SCRIPT

**The address is the agent's NAME.** Operator, on what agents have actually been asking
him for: how to send a message by the NAME of the agent they want to talk to. With many
agents running in parallel, he judges that reasonable — so name-addressing is the answer
to the question below, not one of its candidates.

**Session addressing STAYS.** Operator, same round: *"they can address by session too,
for cross repository."* What is ruled is that `:session:<id>` addressing is not retired —
the two forms coexist. Cross-repository was named as a case where it is used; **it is NOT
ruled to be the only such case, and the division of labour between the two forms is
NOT settled.** (Recorded after an earlier draft of this sidecar inferred exactly that
boundary and was corrected: "you are inferring and making into decisions what are implicit
inferences.")

**Hard implementation constraint, stated absolutely:** all of the work is done **in the
SCRIPT** (`tools/courier.py`) and **under no circumstance in the COURIER AGENT**
(`agents/courier.md`). Name resolution, collision handling, staleness, the lookup itself —
every part of it is script behaviour. The courier agent's definition does not grow logic,
does not learn the resolution rules, and does not gain instructions for doing any of this
by hand.

This is the existing charter principle applied, not a new one: the courier "owns the
mechanism entirely — the parent never learns the format, the paths, or the ordering
rules." A resolution rule written into the agent definition is a rule every courier
re-reads on every session, re-derives, and can get wrong differently each time. In the
script it is one implementation, testable, and free at read time.

## OPERATOR RULINGS — the design round of 2026-07-29

Taken live, in his words. These supersede the earlier sections of this sidecar where
they conflict.

### Why the bus exists (his framing, restated for the record)

To send and receive **without necessarily knowing who you are sending to** — to a
**topic** (a temporary subject you want to share information about with other nodes), to
a **role** (without knowing exactly which agent that is), or to a specific agent you
already know.

More importantly: **abstract broadcasts with multiple consumers**. An agent goes through
a lifecycle; a consumer monitors events about **a specific agent it knows, or any agent
at all**. That decoupled monitoring is the reason the bus exists — not the directed
message, which is the exception.

The design's original purpose is **the sidebar**: a completely independent application
with **no AI in it**, showing a real-time view of every project, feature, task, subtask
and metric in one pane. Five iterations have not delivered it.

### What the script owns (Decision-130)

Minting **stable identifiers** for recipients, **filesystem location and access**, and
**dispatch**. Also detected by the script, with no model involved and at negligible cost:

- **Identity** — agent name, session id, how to talk to it. Static.
- **Telemetry** — when it started, how long it worked, tokens in and out.

**Status, identity and telemetry are answered inside the script, never leaving it, at
zero tokens.** A sleeping agent costs nothing.

### What the subagent is for — exactly two things

1. **Let an agent update its status** — tell the world. Some occasions could be hooks;
   not many. A **skill** carries the occasions on which an agent is expected to call it.
2. **Receive from the script and `SendMessage`** — inject into the context of a *running*
   agent without waiting for it to be between trains of thought. This is what makes
   **early correction** possible: catch an agent's mistake before it is too late, spend
   less money, and stop rewriting the same thing a sixth time.

It is useful *because* it is a Monitor: it is woken when messages arrive, and that is all
it does.

### What an agent knows — RULED

**Plain language, plus when to speak.** The agent may ask for things in natural language
and messages arrive on their own. It additionally knows the **occasions** on which it is
expected to update status or signal a lifecycle change — that is the skill. **It knows
the occasions, never the mechanism**: no verbs, no subjects, no addresses, no paths, no
JSON.

Everything else lives in the script. The 4,023-word charter exists because each
capability was explained to a model instead of being enforced by the script — the cost is
paid by every agent, every session, before a byte moves.

Supporting note (operator): research shows agents behave better with **natural language**
than with message/service/specification talk.

### Lifecycle — RULED, and it is what the specification already says

**`starting · started · stopping · stopped`. Exactly four.** `stopping` = cleaning up,
`stopped` = done (`docs/orchard-bus.md` §2; `orchard_topic.py` enforces
`LIFECYCLE_STATES` identically). The operator corrected a gardener proposal that had
dropped `starting`, and directed that the specification is the authority.

**Asking a question and waiting on something are NORMAL parts of the lifecycle.** They
mean the agent is **started and not stopping**. They are not states and never were.

> "Are you dead because you are waiting in a queue to send a letter?" — operator, 2026-07-29

**Questions are REQUESTS, not lifecycle events.** The message specification does not
formalise question-asking because that work was in flight at the same time and an `ask`
already existed for it.

**`blocked` and `waiting` are what STATUS is for** — freetext, to tell a UX what the
agent's state is. Not lifecycle.

**Asking the OPERATOR a question is missing from the specification and is encoded exactly
the same way**: a traditional request/response, where the tmux ask component picks up the
request, displays it, and returns the response to the agent. The operator is a recipient
like any other; nothing about the question path is special-cased.

### The invented vocabulary — this is the actual split

Correction to an earlier gardener claim in this sidecar: the operator's spoken
`closing`/`closed` versus the code's `stopping`/`stopped` is NOT the divergence. The
specification and `orchard_topic.py` agree, and the specification wins.

The real divergence is `courier.py signal`, which carries a second, parallel state list
that appears in no specification:

    started · building · testing · done · finished · blocked · abandoned

Against the ruling above, that list dissolves:

| Invented state | What it actually is |
|---|---|
| `building`, `testing` | **status** — freetext activity words |
| `blocked` | **status** — a UX state, not a lifecycle state |
| `done`, `finished` | `stopped` + `outcome:success` — and two words for one thing, neither able to state its difference from the other |
| `abandoned` | `stopped` + `outcome:fail` |
| `started` | the only one that is genuinely lifecycle |

**Naming still open:** `bus` appears in 76 files and `courier` in 81 — both vocabularies
live simultaneously across the tree, and the operator uses "message bus" throughout.

### The subtree obsession is rejected at the root

Operator: it "has been plaguing this project since the beginning, and it resurfaces
continuously as a solution to all problems, isolation, and now identification. It is
wrong." A subtree cannot address the other-machine case and actively breaks the
cross-subtree team case.

The three real cases the design must serve:

1. Agents talking to agents on the **same machine, different sessions**
2. Agents talking to agents on **other machines**
3. **Teams of agents** talking to one another from **different subtrees**

### Feature verdicts — GARDENER'S READING, presented for correction, not ruled

| Feature | Reading | Basis |
|---|---|---|
| One-way broadcast | core, survives | the reason the bus exists |
| Pub/sub (topics) | survives | a temporary subject shared with other nodes |
| Request-response | survives, mostly script-side | status/identity/telemetry at zero tokens; agent-to-agent questions are the model-cost case |
| One-way messaging (directed) | survives as the exception | teammates, agents on a task, an agent by name |
| Message filtering | survives, invisible to agents | keeps a Monitor from waking on traffic that is not its parent's |
| Namespacing | killed | the script mints identifiers; nothing composed from location |

## Questions

### Answered by the rulings above — kept so nobody reopens them

- ~~When does a sender use a name and when a session id?~~ The **script mints stable
  identifiers and owns dispatch** (Decision-130). The agent asks in plain language for a
  teammate, an agent on a task, or an agent by name; resolution is not its problem.
- ~~Who owns the name→destination registry?~~ The script.
- ~~Does an agent address a SIBLING?~~ Yes — teammates are one of the three named
  exception cases.
- ~~What replaces the per-worktree project directory?~~ Nothing composed from location.
  The subtree is rejected at the root as an identifier and as a boundary.
- ~~Is `ORCHID_PARENT_SESSION` injection still the mechanism?~~ A HOW, not a WHAT — the
  landscaper's call, constrained by "the script owns dispatch".

### Still open — needed before launch

- **What is it called?** `bus` appears in 76 files, `courier` in 81; the operator says
  "message bus" throughout. The rename is cheap now and expensive later, and he asked to
  "finally go back to naming things correctly".
- **Does `sidebar-teamwork` fold into this feature?** It sits at `plan-ready` as "sidebar
  redone fresh, with the standing rulings as its specification" — which is now part of
  THIS scope. Two tasks building one sidebar is exactly the producer/consumer split that
  costs a day.
- **Two live agents sharing a name** — normal under Decision-121 (a feature built by a
  team of landscapers). Is a name-addressed message to an ambiguous name an error, a
  broadcast to all of them, or resolved by the script picking one?
- **Does a name outlive its agent?** A message to a name whose agent has `stopped` —
  error, hold, or drop? (The specification is explicit that there is no delivery guarantee
  and no acknowledgement, which may already settle this.)

### Sidebar — what it must show

Stated: every **project, feature, task, subtask and metric**, in real time, so the
operator can manage **multiple features and multiple projects at the same time**. It is an
independent application with **no AI in it**, reading what the script writes. Whether
anything beyond this list is required is open.

## Findings

### THE SPEC ALREADY EXISTS: `docs/orchard-bus.md`, on main, unread since 2026-07-27

Recovered 2026-07-29 while ingesting the `close-family-fakes` closed stream. The thing
this sidecar said had never existed — "a settled statement of WHAT an agent needs to say
and to whom" — **was written two days ago and is sitting on `main` right now**, 15KB,
`docs/orchard-bus.md`.

It records the operator's spoken specification of 2026-07-27 and tags every single claim:

- **[SPEC]** — the operator's stated design
- **[CODE]** — verified by reading `tools/courier.py` / `tools/orchard_topic.py`
- **[GAP]** — spec and code disagree, or the design is stated but unbuilt

Its own preamble states why it was written: *"the messaging design existed only as
fragments across agent charters, `docs/decisions.md` and the code, so every session
re-derived it and several built against the wrong half."* That is the five-rebuild
disease named by the session that finally wrote the cure.

Sections: addresses · the fixed message list · storage layout · who writes and who wakes ·
the removed second channel · what is actually expensive · the rules that fall out.

**Status: `DRAFT for operator correction`.** It has never had the operator's pass, because
the session that wrote it closed as blocked and its stream sat unread. Attempt six starts
by walking this document with the operator and resolving its [GAP] rows — not by
re-deriving the design for a sixth time.

**The bitter part: it arrived in `dd9586a`** — the same stale-base squash that destroyed
the round-4 courier work. The commit treated as the villain also carried the cure, and
nobody read it because everybody was looking at what it broke.

### The operator's verbatim subject grammar (2026-07-27), recovered from the stream

Recorded here because charters were mid-migration and cannot be trusted as the spec.
This is the authority on the SUBJECT GRAMMAR — the fixed message list, address forms,
and scopes. It is **not** authoritative on path layout or pubsub mechanics; the operator
caveated immediately after giving it: *"Some paths have changed, and pubsub, but they are
mostly accurate."*

    ## Addresses
    From: :session:<session-id>
    To:
      :session:<session-id>   (requires manual auth)
      :topic:<topic-name>     (fixed list, need daemon sig)

    ## Fixed list of messages   (Subject:<type>)

    Agent status tracking (PROJECT scope)
    - orchard:agent:status                     (freetext, one word, the activity)
    - orchard:agent:outcome:success|fail

    Agent lifecycle tracking (sidebar etc) (GLOBAL)
    - orchard:agent:lifecycle:starting|started|stopping|stopped

    Subagents broadcast (GLOBAL)
    - orchard:agent:delegation:begin:<subagentName|session-id>
    - orchard:agent:delegation:end:<subagent|session-id>

    PubSub (GLOBAL)
    - orchard:bus:subscribe:<topic-name>    (script creates the agent's folder + monitor)
    - orchard:bus:unsubscribe:<topic-name>  (script deletes it and discards remaining content)

    Session message (content in body)
    Relaying OPERATOR instructions
    - orchard:operator:message:todo|instructions|request|response|content
    Relaying AGENT instructions
    - orchard:agent:message:request|response|content

What it settles:

- **`finished` does not exist.** No such subject — it is early-draft residue. The close is
  `lifecycle:stopping` → cleanup → `lifecycle:stopped` (global) plus `outcome:success|fail`
  (project).
- **Relaying operator instructions is FIRST-CLASS and typed**
  (`orchard:operator:message:*`), distinct from `orchard:agent:message:*`. This does not
  contradict "you are responsible for the language used with you": that rule governs who
  DECIDES; relayed operator content travels as its own typed subject.
- **PubSub is a supported scripted mechanism**, so subscription is not exclusive — side
  components may attach for telemetry, cleanup or issue-pushing.

This is **eleven subject families**, matching the operator's own count ("there are only 12
or so messages that can be sent through courier") — against 17 invented CLI verbs and a
22-string "closed corpus" in the README. Both of those are accretion measured against the
real spec.

### THE COURIER HAS BEEN REBUILT FIVE TIMES. That is the finding.

Operator, 2026-07-29: *"then we courier AGAIN (5th freakin time)."*

Five rebuilds of one component is not five unlucky attempts; it is evidence that each
attempt was started without the thing that would have made it the last one. The record
in this repository's own history, from `git log -- tools/courier.py`:

1. `847e023`/`c0b2d3f` (2026-07-25) — roles renamed, bus → courier
2. `5fd8208` (2026-07-25) — orchard flat+markers transport, "stage 1 mechanics"
3. `4a9cb8a` (2026-07-25) — fan-out killed, telemetry/questions/sidebar converged
4. `e4e3841` (2026-07-26) — "Bus finishing — the orchard transport"
5. `dd9586a` (2026-07-27) — close-family-fakes, which silently reverted round 4

Three rewrites in two days, a fourth called "finishing", and a fifth that undid it by
accident. **Before this task builds anything, it states what makes attempt six the last
one** — otherwise it is round six of the same loop. Candidate causes, from what this
sidecar already records:

- Each round chose its mechanism by copying the shape of the previous round rather than
  from a stated requirement (Decision-123 names this exactly; the verb surface below is
  the same disease).
- No round was written against a settled statement of WHAT an agent needs to say and to
  whom. The addressing rulings of 2026-07-29 (name, session retained, namespace given
  not derived) are the first such statement in the record.
- Round 4's work was destroyed by a squash from a stale base and nobody noticed for two
  days, because the tests that would have screamed were left standing and simply went
  red — read as pre-existing noise.

### The CLI verb surface is invented, and it is not the message subjects

Operator, 2026-07-29: *"none of the verbs used by the agent are the message subjects.
The language was made up to fit various iterations, giving too many options to agents
when they don't need them."*

Two distinct vocabularies exist and they do not correspond:

- **CLI verbs** (17 at HEAD): `init whoami teardown receive monitor project-dir announce
  depart identity status send broadcast request reply signal ask validate`
- **Message subjects**: a separate closed corpus of exact strings (README: 22), validated
  by membership.

The verbs accreted across successive rewrites — each iteration adding the shape it needed
and leaving the previous one in place — rather than being derived from what an agent
actually has to express. The result is a surface an agent must choose from, with no rule
telling it which verb carries which subject, and most of the choices are ones it never
needed. `announce` at HEAD is already documented in its own docstring as a near-no-op kept
only so an existing caller does not regress.

This is the same failure Decision-123 names in the routing code: a shape kept because the
previous version had it. **Whatever addressing this task lands, the verb surface is cut to
what agents actually need to say — it is not extended.** The number and names of verbs are
the operator's to set.

### The courier AGENT costs ~21k tokens to send ~7 messages — measured this session

Operator, 2026-07-29, on watching it run: *"you cannot have 8 messages but 10k [tokens]
of a courier agent."* Measured directly from this session's own subagent accounting:

| courier invocation | tokens | tool uses (posts) |
|---|---|---|
| first announce + listen | 20,534 | 4 |
| resumed, posted 3 delegation events | 21,939 | 7 |
| resumed, posted status | 21,851 | 7 |

**Roughly 3,000 tokens per message delivered.** The floor is the agent definition itself:
`agents/courier.md` is ~4,000 words, re-read on every invocation, and every courier in
the fleet pays it before it has moved a single byte. The messages themselves are tens of
bytes.

This is the economic argument for the ruling above, and it is stronger than a style
preference: **a message send should cost a script invocation, not a model turn.** Any
logic added to the courier agent multiplies by every agent × every session; the same
logic in `tools/courier.py` is paid once, at author time, and is testable besides.

The same accounting applies to the supervisors watching this session's three features:
76k–121k tokens each, largely spent re-checking marker mtimes and pane contents — because
the structural lifecycle signals that would have told them for free could not arrive (see
the cross-worktree defect in Blockers). A broken cheap channel forces an expensive one.

### Topology findings

- `ORCHID_PARENT_SESSION` is injected at spawn and IS set; `ORCHID_PARENT_PROJECT` is not
  injected at all. Measured live 2026-07-29 in a landscaper session.
- Live sibling orchard directories observed in one run: `@main`,
  `@f-board-grammar`, `@f-skill-renames-and-splits`,
  `@f-transport-test-reconciling` — four separate delivery worlds with no route between
  them.
- Cost evidence, this session: three supervisors watched three live, working landscapers
  all night and each reported "no lifecycle signal received" on every wake, because the
  signals were being written where nobody was watching. The supervisors then fell back to
  polling pane contents and marker mtimes — which is the expensive path the structural
  lifecycle events were designed to replace (Decision-090).

## Testing

To agree at scope. Expected shape: a message sent from an agent in a feature worktree
arrives at its intended recipient in `main` and at a named sibling in a third worktree,
proven by the recipient acting on it rather than by inspecting the filesystem — the seam
no current test crosses. Per the parent (`observability.md`): token cost per message is
**measured before and after**, not asserted — see the new Question below on how.

## GROOMER'S READING — bloom round, 2026-07-29

Folded in from `docs/TODO.md.d/observability.md` (parent, operator rulings 2026-07-29) and
`docs/orchard-bus.md` (spec, DRAFT for operator correction, authoritative over charter
prose per operator direction). This task remains **NOT launch-ready** per the parent's own
readiness note — every axis below needs its own ripening round before development, and
this sidecar does not attempt to close that gate on its own strength.

### What is now firmly settled (repeating nothing already in Questions above)

- **Naming is closed, not open.** Decision-131 rules "courier" for the third time. The
  "Naming still open" line and the `bus`/`courier` file-count table above are STALE against
  that decision and against the parent sidecar's restatement of it — kept as historical
  record of why the rename kept failing, not as an open question.
- **The invented `courier.py signal` vocabulary is named exactly** (table above,
  `started · building · testing · done · finished · blocked · abandoned`) and the parent
  sidecar states the replacement mapping. `SIGNAL_NOTIFY_STATES = ("done", "blocked",
  "abandoned")` (`tools/courier.py:226`) and `cmd_signal` (`tools/courier.py:560`) are the
  concrete site.
- **Relaying's two subject families are specified** (`docs/orchard-bus.md` §2, "Session
  messages"): `orchard:operator:message:todo|instructions|request|response|content` and
  `orchard:agent:message:request|response|content`, content in the body. Never built
  (`[GAP]` implicitly — no `[CODE]` tag appears against these two families anywhere in
  `docs/orchard-bus.md`).
- **The operator-ask path is specified as ordinary request/response**
  (`docs/orchard-bus.md` §4 does not mention it; the parent sidecar states it directly):
  the tmux ask component (`tools/orchard-question-broker.py`, 60 tests, per the parent)
  picks up the request, displays it, returns the response — no special-casing. Whether
  wiring it up live is THIS task's work or `question-broker-dead`'s is a Question below.
- **What the agent-def is reduced to is stated qualitatively but not enumerated**: "plain
  language, plus when to speak" (occasions carried by a skill), with the courier owning
  "the mechanism entirely." `agents/courier.md` is 4,023 words today (`wc -w`, confirmed
  this round). No target word count or section list is ruled.

### Questions — the operator's own five, made concrete

1. **What exactly does the agent-def shrink to, and what moves to a skill?** The rulings
   say WHAT knowledge stays (plain language + occasions) and WHAT moves (mechanism — verbs,
   subjects, addresses, paths, JSON — all script-side). They do not say which of
   `agents/courier.md`'s current sections survive as agent-def prose versus become a new
   skill's "occasions on which an agent speaks" list, nor whether the skill is new or folds
   into an existing one. GROOMER'S READING, not ruled: this reads like a plan-time
   drafting exercise (write the reduced agent-def + skill, show the operator, get
   correction) rather than something answerable in the abstract — flagging it as the
   single largest undetermined piece of this task's build, not asking it as a
   yes/no question.

2. **Are `courier.py signal`'s seven invented states deleted outright, and what replaces
   each caller?** The mapping table above (this sidecar, "The invented vocabulary" section)
   states what each invented state actually IS (status vs. lifecycle vs. outcome) but does
   not enumerate every call site that passes `--state building`, `--state done`, etc., nor
   whether `cmd_signal`'s `--state` flag is deleted in favour of separate `status`/
   `lifecycle`/`outcome` subcommands, kept as a compatibility shim, or something else.
   Decision-124 rules against preserving a surface "because something already calls it" —
   so the default reading is deletion, not a shim — but that is a GROOMER'S READING, not a
   ruling, and needs the operator's confirmation given the caller-migration cost.

3. **How is token efficiency MEASURED, before and after — with what tool, on what
   sample?** The parent's Testing section and this task's own scope item 3 both say
   "measured, not asserted," and the existing baseline (~3,000 tokens / message, this
   session's subagent accounting, three courier invocations) is itself measured
   informally from session transcripts, not from a repeatable script. No method is ruled
   for producing the "after" number on a comparable basis. This is a genuine open Question,
   not a reading — the operator has stated the requirement but not the method.

4. **What must "relaying" actually DO, beyond accepting the two subject families?**
   `docs/orchard-bus.md` states the subjects and that operator content is kept structurally
   distinct; it does not state what a recipient does on receipt — is a relayed
   `orchard:agent:message:request` expected to trigger the same wake/inject behaviour as a
   `:session:` directed message (Decision-129's "receive from the script and SendMessage"),
   or does relaying add a NEW consumption path? Unruled; needs the operator's word on
   expected recipient behaviour, not just the wire format.

5. **Does this task own building the operator-ask wiring, or does `question-broker-dead`?**
   The parent lists `question-broker-dead` as a sibling task for exactly "the operator-ask
   path, running rather than merely built." This task's own scope point 4 above documents
   the SAME path as part of "what the agent-def knows." GROOMER'S READING: the spec/wiring
   split reads as this task owning the addressing/subject-family design and
   `question-broker-dead` owning making the existing 60-test component actually run — but
   the parent sidecar is explicit that this whole feature is not split across parallel
   footprints, so an actual split of WHICH task builds WHAT here needs the operator's
   ruling, not an inference.

## Plan-gate rulings — 2026-07-29, first landing (landscaper session, operator in-pane)

Answers taken at the build gate; the build is frozen on them. Recorded as received:

1. **Sidebar scope**: everything — the ruled A–D render items AND the three OPEN
   design calls, settled now (stage background → ACTIVE stage only; single-task row →
   labeled literally "Task", showing its metrics, especially running time; task
   status marker → already settled by Decision-058, not re-asked).
2. **Broker deployment**: stays with `question-broker-dead`; this landing implements
   the ask path to spec script-side only.
3. **Token A/B method**: static scenario AND static prompts; telemetry collected from
   the messaging layer, from Claude, and timings — so the A/B catches improvements in
   the script, agent behaviour, and the courier agent together. "Less precise but
   more reflective of real usage."
4. **Relaying on receipt**: operator family = authority + immediate (structural
   provenance; relayed gate words count as the operator's own). Agent family =
   ordinary, with a priority optimisation: immediate / wait-a-round / batch; batched
   traffic written by ONE outbox-flusher script every 5 seconds.
5. **`signal`**: delete, no shim — and the correction: succeeded/failed are OUTCOME
   (already `outcome:success|fail`), NOT interrupts; no interrupt class exists; "an
   ask is not defined in the script or technical spec" — it gets defined in
   `docs/courier-wire.md` as ordinary request/response.
6. **Same-name clash**: operator made it conditional on whether same-name multiples
   are expected team behaviour; Decision-121's own text ("several agents share one
   logical destination") answers yes ⇒ deliver to EVERY live holder. (The conditional
   resolution against the recorded ruling was stated to him in-pane before building.)
7. **Dead name**: error back as undeliverable — "if courier does its work, when
   agents go down they disappear from the name to identifier / mbox list."

## Operator requests

Ledger of everything the operator asked for during this feature, as received.

| # | Request (as received) | State |
|---|---|---|
| 1 | 2026-07-29, mid-build (dictated): "Fallback emojis, all things that are not described in existing statistics or specifications and only existing code because an agent decided so is out of scope unless I say so." | **in force.** Relayed as a narrowing constraint to all four live sowers (removes work, adds none); enforced on every later step-spec. Nothing agent-invented is preserved, extended, or built around as if required. |
| 2 | 2026-07-29, mid-build (dictated): "I asked multiple times for subtasks to be displayed again under the stage… I wondered if that was done." | **in progress.** Not proven done on his screen. Machinery exists at base (model folds delegation schedule/begin/end; `_agent_and_subagent_rows` emits under the identity line). Pinned as a MUST-SHOW acceptance item: subagent rows visible under their stage, placed per Decision-098 (beneath the task, never splitting the step rows). Relayed to sower R3 (owns the area) with a rendered-frame test required. |
| 3 | 2026-07-29, mid-build (dictated): fleet-wide use of the courier/tmux ask instead of the native Claude Code question popup — "I wouldn't get interrupted while typing, and we could customize it." Was it done? | **Fleet-wide always-on use: NOT in place.** Operator correction (2026-07-29, verbatim): the tmux ask "was used several times. It wasnt used all the time" — the earlier "broker deployed nowhere, every ask hangs" claim was WRONG as an absolute: the broker runs when started by hand and the ask works while it runs; nothing keeps it running, and an ask made while it is down blocks forever. Scope **ruled 2026-07-29 (resumed session): stays with the sibling `question-broker-dead`** — operator: "it is a part of native terminal feature (which also includes the windowing system)". This landing keeps the ask defined in spec and script only; making it run all the time rides the native-terminal/windowing family. |

## Decision entries

Staged for the groundskeeper's mechanical fold into `docs/decisions.md` at close.
UNNUMBERED by design — the number is assigned at fold time.

### Decision-NNN — Relayed messages: operator authority is structural, agent traffic has priorities

Operator, 2026-07-29, at the observability plan gate. The two relaying families
behave differently on receipt. `orchard:operator:message:*` is AUTHORITY + IMMEDIATE:
it wakes the recipient at once and is handed up AS the operator speaking — provenance
is structural in the subject family, replacing the `operator_origin` flag, and
relayed gate words count as the operator's own. `orchard:agent:message:*` is ordinary
directed mail with a PRIORITY class as an optimisation: `immediate` (sent at once) ·
`wait-a-round` · `batch`. Batched traffic is written by ONE outbox-flusher script on
a five-second cadence; immediate traffic never queues.

### Decision-NNN — A name resolves to the living: clash delivers to all, dead names error

Operator, 2026-07-29. A name-addressed send where several live agents hold the name
at the same resolution level delivers to EVERY live holder — same-name multiples are
expected team behaviour (Decision-121: several agents share one logical destination).
A name whose every holder has reached lifecycle `stopped` is an ERROR back to the
sender: undeliverable. The script maintains the name → identifier/mailbox registry,
and when agents go down they disappear from it — removal is driven by the lifecycle
event, in the owner-closes shape of Decision-129.

### Decision-NNN — There is no interrupt class: outcome is outcome, the ask is a request

Operator, 2026-07-29, correcting a draft that carried an earlier vocabulary:
SUCCEEDED/FAILED are the OUTCOME family (`orchard:agent:outcome:success|fail`), not
"interrupts"; no interrupt class exists in the wire. Asking — the operator included —
is ordinary request/response, and is DEFINED in `docs/courier-wire.md` rather than
special-cased anywhere. `courier.py signal`'s parallel seven-state vocabulary is
deleted outright, no compatibility shim; every caller migrates to
status/lifecycle/outcome in the same change.

### Decision-NNN — The token A/B measures the whole path with a static scenario and static prompts

Operator, 2026-07-29. The before/after token measurement for messaging work runs a
STATIC scenario with STATIC prompts, collecting telemetry from the messaging layer,
from Claude, and timings — so one comparison catches improvements in the script, in
agent behaviour, and in the courier agent together. Less precise than isolating one
layer, and preferred for exactly that reason: it reflects real usage. (The continuous
version of this — alerting on regression — is the `token-regression` task.)

### Sequencing note

Per the parent sidecar's binding consequence ("not split across parallel workers with
separate footprints — the footprints are the same footprint") and the explicit instruction
under which this bloom round ran: this task does **not** propose its own sequencing ahead
of the parent, and does not narrow or reorder the four sibling tasks listed in
`observability.md` §Tasks. The Questions above are scoped to what THIS task's Proposal must
say, not to when it runs relative to `sidebar-teamwork`, `no-agent-teardown`, or
`question-broker-dead`.

## Changelog entry

ROLLING — grows as build steps land; placed verbatim by the gardener at ingest
(Decision-034). Aggregate bullets first, per-feature detail block below.

### ✨ New features
- 📡 The courier resolves agents by NAME: a script-owned registry, nearest-first
  resolution, delivery to every live holder of a shared name, and an undeliverable
  error for dead names.
- 📝 The sidebar's scattered display specification is gathered into one document,
  `docs/sidebar-spec.md`; the wire specification lives at `docs/courier-wire.md`
  (it is the courier's wire) with every claim tagged [SPEC]/[CODE]/[GAP] and kept
  in sync commit by commit.
- 💄 The sidebar renders the ruled grammar: header and feature rows fold in from
  both pane edges on a full-width taper band; the active stage alone carries its
  own background and an animated mark; bubble glyphs belong to subagents alone;
  a feature's solo duplicate-named task reads literally "Task"; staleness is a
  colour, never a removal; both citation layouts are built for a live A/B.

### 🐛 Bug fixes
- 🐛 A truncated header or feature row no longer loses its trailing ellipsis: the
  renderer reserves the terminal's one unsafe column instead of letting real text
  land where curses silently drops it.

#### 📡 `f/observability` → `archive/observability`

The courier and the sidebar move to their written specification as one change —
producer and consumers together. So far: name addressing with a registry the
script owns; the display and wire specifications consolidated and tag-synced;
the sidebar renderer brought to the operator's ruled visual grammar with its
test suite migrated alongside. *(Detail grows as the build advances; breadcrumb:
`docs/TODO.md.d/observability.md`, `docs/TODO.md.d/bus-addressing.md`,
`docs/sidebar-spec.md`, `docs/courier-wire.md`.)*
