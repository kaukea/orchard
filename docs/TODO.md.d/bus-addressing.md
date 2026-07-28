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
