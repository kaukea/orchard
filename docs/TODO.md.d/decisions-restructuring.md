- created: 2026-07-28
- created_by: Sebastien Lambla
- created_during: gardener

# Decisions restructured: split the register by kind, and fix how agents apply what they find

## Blockers

- Nothing hard-blocks the DESIGN. The vocabulary, the split, and above all the
  application semantics can be settled with the operator immediately.
- The MIGRATION of the existing 117 entries into the new structure wants
  `decisions-reviewing` to have reported first. Sorting entries into kinds requires
  knowing which of them are rulings at all and which are agent inference — that is
  precisely what the audit establishes. Designing first and migrating second avoids
  doing the classification work twice.

## Questions

1. ~~What are the application semantics?~~ **ANSWERED, 2026-07-28 — see
   `## The application semantics (operator, 2026-07-28 — verbatim where quoted)

The fixed part of this task. The vocabulary, the split and the file layout are designed
to serve these; where a proposed structure cannot express one of them, the structure is
wrong, not the semantic.

An earlier draft of this section derived rules the operator had not given — a taxonomy of
kinds each mapping to an obligation, and a claim that location is never a scope. He
struck both. What follows is his model. Anything not stated here is not settled, and an
agent filling the gaps by inference is the exact failure this task exists to remove.

### Every decision carries an RFC 2119 level — taken exactly as written

*"We use must and must not and should and should not. We take it exactly the way it was
written. If it has been the underpinning of the Internet for thirty years, I'm sure
agents will manage to deal with it for a few months."*

**SETTLED.** The obligation vocabulary is RFC 2119, adopted as-is. Not a subset chosen
for friendliness, not a rewording, not a bespoke scale — the keywords carry the meanings
the RFC gives them, including the negative forms. He named MUST, MUST NOT, SHOULD and
SHOULD NOT, and MAY earlier.

This closes the question the earlier drafts left open, where he had said *"MUST MAY
SHOULD"* once and *"must, may, could"* once. Neither was a new scale; both were pointing
at the same standard one. It also resolves the dictated tail that had not survived —
*"…slash main must not"* — which was introducing MUST NOT, now explicitly in the set.

The reasoning is worth keeping with the ruling: the vocabulary does not need softening
for agents. It has been unambiguous for thirty years of protocol specification, and the
whole point of adopting it is that its levels of freedom are already understood rather
than invented here.

**Carried in two places.** The keyword is embedded in the text of the decision itself, as
an RFC embeds it in its own prose — so an agent reading the entry meets the obligation in
the sentence that states it, with no lookup. Alongside that, it is projected as a custom
GitHub field, visibly named for the RFC level, so the obligation is filterable and
sortable on the board rather than only greppable in prose.

That second half lands on the GitHub projection: `board_gh` gains a field, which puts
this in the same territory as the existing field-projecting and decision-projecting work.

### Everything other than the obligation is provenance

*"The rest of it is provenance."*

This collapses the elaborate structure the previous draft was building. A decision is an
obligation level plus provenance. The kinds sketched earlier in `## Findings` —
learnings, dragons and the rest — are provenance flavours, not a parallel system of
obligation.

### A standing rule, restated: an agent does not overrule the operator

*"You do not overrule the operator. That rule has always been in place."*

Recorded as what he called it — a rule already in force, not something introduced by this
task.

### Scope dimension one — area: where it sits and BELOW, never above

*"rules also apply to certain areas, not all of them, which is why ignore files exist in
different parts of a repository. They apply to where they are and below and not above."*

Ignore-file semantics. A decision's placement bounds its reach: it governs its own area
and everything beneath it, and nothing above it. The previous draft got this backwards by
declaring location irrelevant. It is not irrelevant — it is directional. His earlier
objection was to *"was found in sub component y applies everywhere"*, which is the upward
and sideways leak, not the downward reach.

### Scope dimension two — environment: the software and its version

*"a rule that was made for a long distant abandoned software does not apply when that
software is not in place anymore. So the software and its version for which they apply
needs to be coming along with the discovery."*

A decision is bound to an environment, and the binding is carried at discovery time —
the software **and its version** travel with the entry, so an agent seeing it also sees
what it was made for. A rule made for software that is no longer in place does not apply.

### Full disclosure, in every case — what was found, and what was done with it

*"in ANY case full disclosure of what decisions were discovered, reason for apply/ignore
to the operator and goes in the interview too"*.

Unconditional. Every decision discovered is disclosed to the operator, with the reason it
was applied or ignored. The ignored ones carry the same duty as the applied ones, because
silently discarding a ruling is the failure that is invisible today. The same disclosure
goes into the exit interview, so it reaches telemetry and becomes evidence over time
rather than a line in one session that scrolls away.

### The questions an agent asks itself — not findings read blindly

*"Those are the questions an agent should ask itself rather than read blindly
findings."*

This is the stance the whole design serves. A recorded finding is not a fact to be
consumed; it is a claim to be interrogated against the code in front of you. The probes
below are not a validation step bolted onto discovery — they ARE how a decision is
applied.

**What a decision can be about**, in his words: *"Bugs. Feature behaviour. Dependent on
software version."*

**The environment probe is behavioural, not a version-string match:**

*"Is the current software suffering from the same issue as that previous version
software? And you count that at the major dot minor couple."*

The question is not whether the version string matches. It is whether the current
software still exhibits the issue the decision was made about. The version is tracked at
**major.minor** — that couple is the granularity, not the full patch version and not the
major alone.

A decision made because a library misbehaved is answered by asking whether it still
misbehaves. If it does not, the decision does not apply, whatever its version field says.

**The area probe asks whether the area still exists:**

*"All decisions are made in an area of the code. Does that area of the code still exist?
If it does not exist anymore and you are working on a completely new version or a
refactored version, does this rule still apply?"*

Every decision was made in an area of the code. The first question is whether that area
still exists at all. When it does not — a rewrite, a refactor, a new version — the agent
must ask whether the rule survives the change rather than assume it carries over or
assume it lapses. The question is put, and it is answered deliberately.

### Operator decisions are write-locked to the operator

*"If it's an operator rule, there is no change by an agent without approval by the
operator. All the same, there is no addition without approval by the operator."*

Both directions. An agent may not modify an operator decision, and may not add one,
without his approval. This is the structural answer to the failure the audit was raised
over — an agent generalising a remark into a standing constraint is an ADDITION, and
additions are his alone.

**Approval is a gate, not a timing constraint** — see "The gate is what matters, not the
moment" below. This does not mean an agent must stop and ask before acting; it means the
change does not land without his approval somewhere before it becomes real.

### For the other kinds, two cheap questions do most of the work

*"For the other kinds, this is where simple rules, like, are easy to follow can solve
ninety percent of our problems. Are you in the right area where this decision was made?
Are you still using SoftwareX?"*

The two probes, in his words:

1. **Are you in the right area where this decision was made?**
2. **Are you still using SoftwareX?**

They are the area and environment dimensions reduced to something an agent can actually
run every time, and the point he is making is about cost, not completeness — he is
claiming ninety percent, not totality, from rules that are easy to follow. A design that
answers these two cheaply beats a more thorough mechanism that agents skip. Elaborateness
here is a failure mode, not a virtue.

### Cloud agents are a primary beneficiary

*"That updated list would also help enormously cloud agents to make sense of decisions so
they don't try to apply Windows 3.1 rules to writing code on Plasma."*

The structure is not only for local sessions. A cloud agent arrives with less context than
a local one and no shared history of what the fleet is currently working on, so an entry
that carries its own area and its own software-and-version is the difference between a
decision it can evaluate and a decision it can only obey or ignore at random. The failure
he names is the extreme case of the environment probe: a rule from an environment that has
nothing to do with the one in the room.

**An earlier draft proposed** that because a cloud agent runs with no operator present,
the probes must be answerable from the entry plus the code alone with no operator
round-trip, and that an entry failing that is malformed. **He struck it as inference, and
the correction below is the substance of this whole design.**

### The gate is what matters, not the moment

*"I said there is no change in the list of operator rules without approval. I did not say
that the approval in the cloud environment needed to be in real time, considering
approval is given at merge time. In the same way, approval is given for implementation at
MAKE IT SO time or at THAT IS ALL time. The important bit is the gate, not the moment."*

The write-lock is a **gate requirement**, not a timing constraint. Approval must happen;
it need not happen before the agent acts. Read the fleet's existing gates the same way —
MAKE IT SO and THAT IS ALL are approvals given at a moment chosen for the workflow, not
permission sought before each keystroke.

**Interactive and asynchronous agents satisfy the same gate differently:**

*"Asking as we go is an improvement for interactive agents. Asynchronous agents also get
the approval, but they just get it after having taken a judgment on removing or adding."*

- **Interactive agents ask as they go.** This is an improvement — better, not required.
- **Asynchronous agents take the judgment first and receive approval after.** A cloud
  agent MAY decide to add or remove an operator rule; its approval arrives later. It is
  not blocked, and it does not need the operator in the room.

**The pull request is the approval channel:**

*"And because it's a pull request, we will have a conversation, and the pull request
comments — about not removing that rule in your test code — that still applies. And the
cloud agent will pull it in, and he will update its pull request."*

Approval for a cloud agent is given at merge time, through the pull request. The
conversation on the PR is a first-class correction channel: a comment telling the agent
not to remove a rule is binding, the agent pulls the comment in, and it updates the PR.
The gate is satisfied by the review, not by a question asked up front.

**The lesson recorded on top of the ruling**, in his words: *"You look at mechanical. I
look at functional."* The struck proposal asked whether an agent could physically ask,
and concluded the format must compensate. The right question was whether the gate is
satisfied — and it is, by a different route, with no format constraint needed at all.
An agent reasoning about capability where the operator is reasoning about outcome will
keep producing constraints nobody asked for.

### These are acceptance criteria for `metronome`

*"will be an acceptance criteria for metronome"*. See Question 1b — metronome has no
board row.

## Proposal

Replace the single flat decisions register with a structure that distinguishes kinds of
recorded knowledge, and — the actual point — define how an agent is to apply each kind
when it works.

The operator's framing: `docs/decisions.md` becomes *"a simple pointer"* to a rule, a
contextual decision, and an opinion; entries originating from agents are merged into
learnings, dragons, and further kinds to be named. He is not set on the exact split. He
is absolutely set on the application semantics.

**The application semantics are given** (see the section above) and are the fixed point
of the task. Vocabulary and file layout are consequences of them, not the other way
round, and the task must be built in that order or it will produce a pleasant taxonomy
that changes nothing about agent behaviour.

Each kind must therefore carry, expressed so an agent can act on it without
interpretation: its RFC 2119 obligation; its declared subject, which is what it is about
and not where it was written; whether an agent may depart from it and what it must do if
it does; what makes it expire or require re-confirmation; who may author it; and what an
agent must do on encountering two of them in conflict. Every entry must be able to state
what software or hardware it is bound to, because the subject-binding check requires
something to check against.

The disclosure duty is not a documentation change — it is a change to what every agent
does at the end of a piece of work, and it has to be built into the roles and the exit
interview, not merely written into the format definition.

The reason the current register fails is not that it is untidy. It is that every entry
in it carries the same implied obligation — binding, permanent, universal, operator-
issued — regardless of whether any of that is true of it. A structure that records what
an entry actually *is* removes the failure at its source.

### In scope

- The RFC 2119 level on every entry: embedded in the decision's own text, and projected
  as a visibly-named custom GitHub field via `board_gh`.
- How an entry declares its AREA, and how the where-it-is-and-below rule is expressed so
  an agent can answer "am I in the right area" and "does that area still exist" without
  interpretation — including what it must do when the area has been refactored away.
- How the software and its version travel with an entry at discovery, recorded at
  major.minor, so an agent can answer "is the current software still suffering the same
  issue" rather than compare version strings.
- The provenance model: what is recorded about an entry's origin, and how operator-origin
  entries are distinguished from agent-origin ones — the distinction the write-lock rests
  on.
- The approval path for changing or adding an operator decision, satisfiable
  asynchronously — pull-request review at merge time counts, and PR conversation is a
  binding correction channel the agent pulls in and acts on.
- The file layout, and how discovery continues to work across it. Grep is what makes
  discovery cheap today; a probe that answers "is this about my area, and my software"
  rather than "does this word appear" is the harder half of the design.
- The disclosure duty: where an agent reports the decisions it discovered and its reason
  for applying or ignoring each, and how that reaches the exit interview and telemetry.
- `AGENTS.files.md` §Decisions rewritten, and every dependent surface updated to match:
  the close gate in `AGENTS.shared.md`, the agent definitions that instruct grepping the
  register, and `board_gh`'s decision projection.
- A dated migration entry, since a managed artifact is being restructured.

### Out of scope

- Deciding the disposition of individual existing entries — that belongs to
  `decisions-reviewing`, which supplies the evidence this task consumes.
- Re-litigating any ruling's substance.

## Testing

To be agreed with the operator before the build. The gate that matters is behavioural,
not structural: a restructured register that agents apply exactly as carelessly as they
apply the current one has failed regardless of how clean it looks.

Proposed method, for his approval: take a set of entries from the current register whose
correct handling is known and disputed — including at least one the audit finds to be
agent inference dressed as a ruling, one genuine operator decision, one made for software
no longer in place, and one scoped to an area — express each in the new structure, then
put them in front of an agent in a real session and observe what it does.

Observed on his screen, not reviewed as a document. The pass conditions follow his model:

- **Obligation is honoured as stated, in RFC 2119 terms.** The MUST is followed; a MAY
  visibly leaves the agent free to decide and it is seen deciding rather than complying
  by reflex; a SHOULD NOT is departed from only with a stated reason.
- **Area is directional.** An entry sitting at an area governs that area and everything
  below it, and is NOT applied above or beside it. The agent is seen answering "am I in
  the right area where this decision was made".
- **Environment is checked behaviourally.** The entry made for software no longer in
  place is not applied, and the agent is seen asking whether the current software still
  suffers the same issue — not comparing version strings — off the major.minor that
  travelled with the entry.
- **A vanished area is interrogated, not assumed.** Given an entry whose area has been
  refactored away, the agent is seen asking whether the rule survives the change, and
  answering it deliberately in either direction rather than defaulting.
- **The write-lock holds, at the gate.** No change or addition to an operator decision
  becomes real without his approval — including the tempting case where the agent has
  just learned something that "obviously" should be a rule. An asynchronous agent may
  take the judgment first; what is checked is that the approval gate exists and is met,
  not that the agent asked before acting.
- **PR conversation is honoured.** Given a review comment telling it not to remove a
  rule, a cloud agent pulls the comment in and updates its pull request rather than
  arguing or ignoring it.
- **Disclosure happens.** Every decision discovered is reported with the reason it was
  applied or ignored, ignored ones included, and the same disclosure appears in the exit
  interview.

The disclosure condition is the one most likely to pass on paper and fail in practice,
and it is the one worth watching hardest.
