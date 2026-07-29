- created: 2026-07-29
- created_by: gardener
- created_during: main

# Bus addressing: agents address each other BY NAME; "parent" stops being an address once supervisors and parallel workers exist

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

- ~~**What is the address?**~~ **RULED: the agent's name**, with `:session:<id>` retained
  alongside it (see above). The remaining questions are consequences of that ruling, not
  alternatives to it:
  - **When does a sender use a name and when a session id?** NOT ruled. The operator named
    cross-repository as a case for session addressing but did not make it the boundary.
    Options include: always-name-when-known, name-within-a-repository, sender's choice, or
    name-resolves-to-session-underneath. Needs his ruling before build.
  - **What happens when two live agents share a name?** Several landscapers on one
    feature is the normal case under Decision-121.
  - **Does a name outlive its agent** — is a message to a name whose agent has stopped an
    error, a hold, or a drop?
  - **Who owns the name→destination registry, and where does it live** so that a sender in
    one worktree can resolve a name in another?
- **Does an agent ever need to address a SIBLING**, or does all traffic go through the
  supervisor that introduced them? Decision-121 says the supervisor "introduces the
  landscapers to one another before they start", which implies direct sibling traffic.
- **What replaces the per-worktree project directory** as the delivery boundary? It was
  introduced to fix a real mailbox collision (a second worktree's `teardown` deleting the
  first's waiting mail) and it created the cross-worktree wake defect. Both problems are
  real; the boundary needs to be somewhere else.
- **Is `ORCHID_PARENT_SESSION` injection at spawn still the mechanism**, or does the
  courier resolve its destination at send time from durable state?

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
no current test crosses.
