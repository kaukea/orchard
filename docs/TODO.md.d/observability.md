- created: 2026-07-29
- created_by: gardener
- created_during: main

# Observability: a distributed, loosely coupled fleet you can actually watch

## Proposal

**Operator ruling, 2026-07-29. The feature is OBSERVABILITY, with the tasks that go with
it.** It is the last attempt: *"everything, this is the last go before i go to chatgpt."*

The deliverable is that the operator can **manage multiple features and multiple projects
at the same time**, by looking at one pane, because the fleet publishes what it is doing
and anything can watch. Five iterations have produced a transport and no observability.

What it contains, in his words:

1. **The courier implemented to its specification** — spec built, testable and tested,
   token efficient, a base for communication rather than a sixth rewrite.
2. **The lifecycle implementation** — `starting · started · stopping · stopped`, emitted
   faithfully, with `outcome:success|fail` as the separate contract other tools consume.
3. **Cleaning after `THAT IS ALL` uses the CLOSED EVENT** — the close stops being a
   choreography of who tells whom, and becomes a consequence of an agent reaching
   `stopped`.
4. **Removing all relevant hard-coded agent-to-agent communication**, for a **distributed,
   loosely coupled model**. Agents stop knowing each other's topology.
5. **The supervisor SUPERVISES and LISTENS.** It does not poll pane contents, does not
   read marker mtimes, and is not told the pipeline's shape in prose. It watches events.
6. **The sidebar**, systematically displaying this information: an independent application
   with **no AI in it**, showing every project, feature, task, subtask and metric in real
   time.

### Why these are ONE feature and not six

**Operator, verbatim: *"every time someone tries to change one without taking into account
the other, you ruin a day of my work."***

The producer and its consumers are one change. A round that alters what the script emits
without altering what reads it — or teaches a reader a shape the script does not send —
costs a day, and has done so repeatedly. Binding consequences:

- **No partial landing.** Script, agent-def, skill, tests and sidebar land together.
- **Not split across parallel workers with separate footprints** — the footprints are the
  same footprint.
- **A change to an emitted shape updates every reader of that shape in the same commit.**
- **The test that matters is end to end**: an agent emits, and the sidebar shows it. A
  green unit test on one side alone does not exercise the seam that keeps breaking.

### The governing principle

**Delegate the maximum of the functionality to the SCRIPT** — to reduce both token cost
and the "creativity" of the models (operator, 2026-07-29).

The script already enforces every rule: **no message that does not respect the format, or
whose subject is unknown, was ever accepted.** Enforcement exists. The waste is the
4,023-word agent-def that re-explains that enforcement to a model, in every agent, in
every session, before a byte moves — currently about **3,000 tokens per message
delivered**.

**Freedom lives in the BODY.** The envelope is closed and enforced; the body is open. An
agent with something unusual to say says it in the body — never by inventing a subject, a
verb, or a state.

### What an agent knows — RULED

**Plain language, plus when to speak.** It asks for things in natural language; messages
arrive on their own. It additionally knows the **occasions** on which it updates status or
signals a lifecycle change — carried by a **skill**. It knows the occasions, **never the
mechanism**: no verbs, no subjects, no addresses, no paths, no JSON.

Supporting note (operator): research shows agents behave better with **natural language**
than with message/service/specification talk.

### Lifecycle, status, outcome, requests — the four things, kept apart

- **Lifecycle** — `starting · started · stopping · stopped`, exactly four
  (`docs/orchard-bus.md` §2; `orchard_topic.py` already enforces it). `stopping` =
  cleaning up, `stopped` = done.
- **Status** — freetext, one word, for a UX. `blocked` and `waiting` are STATUS.
- **Outcome** — `success | fail`, the contract other tools consume.
- **Requests** — questions, including questions to the operator.

**Asking a question and waiting on something are NORMAL parts of the lifecycle**: they
mean the agent is *started and not stopping*. They are not states.

> "Are you dead because you are waiting in a queue to send a letter?" — operator, 2026-07-29

**Asking the OPERATOR is a request like any other**: the tmux ask component picks up the
request, displays it, and returns the response — traditional request/response, no
special-casing. The component already exists (`tools/orchard-question-broker.py`, 60
tests) and is simply not running, which is why every `ask` in the fleet currently hangs.

### Identification (Decision-130)

**The script mints stable identifiers, and owns filesystem location, access and
dispatch.** An agent asking to talk to a named correspondent — a teammate, an agent
working on a task, an agent by name — is the **exception**. The rule is publish and
monitor: a consumer watches events about a specific agent it knows, or about **any agent
at all**.

**The subtree is rejected at the root** as identifier and as boundary. Operator: it *"has
been plaguing this project since the beginning, and it resurfaces continuously as a
solution to all problems, isolation, and now identification. It is wrong."* It cannot
address the other-machine case and it breaks cross-subtree teams.

The three cases the design serves:

1. Agents on the **same machine, different sessions**
2. Agents on **other machines**
3. **Teams of agents** across **different subtrees**

### Encapsulation and loose coupling (Decision-129)

**If you opened it, you close it.** The courier closes its own Monitor because the courier
armed it. A component that manages a resource is asked to create it, and then **listens
for the finish** to destroy it — it is never called back and told to clean up. That
listening step is the decoupling, and it is what survives an agent dying without making
the call.

### Relaying — specified, never built, wanted

Operator: *"We didn't implement relaying but this is also a powerful tool."*
`orchard:operator:message:todo|instructions|request|response|content` and
`orchard:agent:message:request|response|content`, with operator content kept as its own
family so provenance is **structural** rather than a flag someone remembers to set.

### Naming (Decision-131)

**It is the COURIER.** Ruled for the third time. Every remaining `bus` in the tree is a
leftover, including `docs/orchard-bus.md`'s own filename.

### Teams across worktrees — pub/sub, set up by the supervisor (Decision-133)

A team may have three worktrees with a teammate in each, and they must be able to talk.
The mechanism is **pub/sub**: subscribe to a topic **for the current feature or task**,
then talk freely to everyone working on it, **depending on how the SUPERVISOR set it up.**

The topic is the address — which is how the cross-subtree case is served without the
subtree ever becoming one. Owning which topic exists and who is on it is the supervisor's
first concrete duty under "supervise and listen".

### Resolution and permissions (Decision-132)

**Nearest-first:** an agent asked for resolves to the one in your own subtree; failing
that, walk up until only main has one, and deliver there. **Hard rule:** outside your
tree, an agent may **only ask questions or query status**. Inside, everything is fair
game. Enforced by the script, not by prose.

Open, and NOT to be assumed by an implementer: whether teammates sharing a topic gain
rights across a tree boundary that non-teammates do not.

## Tasks

- `bus-addressing` — the courier implemented to specification
- `sidebar-teamwork` — the sidebar, folded in per this ruling
- `no-agent-teardown` — the window closed by its creator on the lifecycle event
- `question-broker-dead` — the operator-ask path, running rather than merely built

## OPERATOR ANSWERS — ripening round, 2026-07-29

### Token efficiency: A/B passes today, but the FEATURE is regression alerting

Operator, verbatim: *"A/B is a good test to pass today, the feature we need is token
regression: Same scenario implementation, collect telemetry from messaging and from claude
and timings and alert when there is regression"*.

So an A/B measurement satisfies the testing gate for this feature, but the thing he
actually wants built is a **token-regression harness**: a fixed scenario, run repeatedly,
collecting telemetry from **the messaging layer**, from **Claude itself**, and **timings**,
that **alerts on regression**. Tracked as its own task (`token-regression`) because it
outlives this feature — it is how every later change is kept honest.

### The metrics — ALL FOUR, and the specification already exists

Ruled: **time · tokens in and out · context remaining · model and effort**.

Operator, with emphasis: *"All this has been specified to DEATH including the behaviour of
the 5 steps, the $ cost per feature, the floor time and active time for a feature, the
running time for a task, it's all in there."*

So the sidebar specification is NOT to be re-elicited. It already covers, at minimum:

- the behaviour of the **5 steps**
- **$ cost per feature**
- **floor time** and **active time** for a feature
- **running time** for a task

**FINDING (gardener, this round): it is real, but it is SCATTERED.** The material lives
across at least `sidebar-teamwork.md`, `sidebar-empty-rows.md`, `sidebar-titling.md`,
`features-first-class.md` and `bus-message-specifying.md`. That dispersal is why rounds
keep asking him again for things he has already specified. **Consolidating it into one
place is part of this feature's work, and no round may ask the operator to restate any of
it.**

### The abandoned work is KEPT, and compared at the end

Operator: *"If it has dracula in it its the latest. The previous one has the metrics I
want, the dracula one has more or less the UX I want, but I don't know that either is
connected to courier correctly."* And: *"keep the branch, we'll compare at the end, it did
have a lot of good things but may not be the right implementation, let's not lose it."*

Verified preservation status, 2026-07-29:

| Artifact | State |
|---|---|
| `archive/sidebar-teamwork` → `04aff25` | **intact**, and it CONTAINS the Dracula commits (`0658677`, `e39fed8`, `9a91fd9`) |
| `stash@{0}` — on `f/sidebar-teamwork`, `sower-b8-check` | **retained, untouched** |
| `stash@{1}` — on `close/bus-transport-v2`, "The event list is the shipped lifecycle vocabulary" | **retained, untouched** |

So both halves he named survive: the **Dracula UX** and the **earlier metrics** are both
reachable from the archive tag. Nothing is dropped, nothing is applied. **At the end of
this feature, both are compared against what was built** — his stated intent, not an
optional nicety. His open doubt stands and must be answered by that comparison rather than
assumed away: *neither may be connected to the courier correctly.*

### Close-on-event needs a WINDOWING MANAGER, and it is pluggable

Operator, verbatim: *"It needs synchronisation between the supervisor, and a windowing
manager (currently tmux) that gets the delegations, so other window managers can be
implemented (it was a feature i was to be working on today)"*.

This is Decision-114's placement component made concrete:

- A **windowing manager** component **receives the delegations** — it is told what to place,
  not how to place it.
- **tmux is the current implementation, not the interface.** Other window managers must be
  implementable against the same surface.
- It **synchronises with the SUPERVISOR** — which is what "the supervisor supervises and
  listens" means in practice on this axis.
- Per Decision-129 it also **closes what it opened**, by listening for the lifecycle event
  rather than being called back.

## Readiness — NOT launch-ready

**Operator, 2026-07-29: "each of those axes will probably need an extra round of ripening
before it goes to development."**

The rulings recorded here settle the WHAT at feature level. They do NOT make any single
task launch-ready: each axis gets its own ripening round first, and no landscaper is
spawned on the strength of this sidecar alone.

## Testing

End to end, and agreed at plan: an agent emits, and the operator's sidebar shows it —
across more than one feature and more than one project at once, which is the stated
purpose. Token cost per message is **measured before and after**, not asserted. A close
runs to completion driven by the `stopped` event with no agent calling a teardown.
