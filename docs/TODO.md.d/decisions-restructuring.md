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

### Every decision carries an obligation level — MUST, MAY, COULD

*"decisions in general, whatever the context, global or not, all map every single one of
them to MUST, MAY, COULD, which gives a pretty well understood level of freedom for an
agent to decide if it will follow or not."*

Every decision. Not a taxonomy of kinds where some bind and others do not — each entry
individually carries a keyword, and the keyword is what tells an agent how much freedom
it has to not follow. The obligation is the well-understood part precisely because these
words are already understood; nothing bespoke is introduced.

Unsettled: **the exact keyword set.** He has said *"MUST MAY SHOULD"* once and
*"must, may, could"* once. Whether the third level is SHOULD or COULD, and whether the
negative forms are available, are his to fix and must not be assumed.

Unresolved: his sentence ended *"…needs to be coming along with the discovery slash main
must not"*. The tail did not survive dictation. It may be introducing MUST NOT. It is
recorded here rather than guessed at.

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

### Operator decisions are write-locked to the operator

*"If it's an operator rule, there is no change by an agent without approval by the
operator. All the same, there is no addition without approval by the operator."*

Both directions. An agent may not modify an operator decision, and may not add one,
without his approval. This is the structural answer to the failure the audit was raised
over — an agent generalising a remark into a standing constraint is an ADDITION, and
additions are his alone.

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

- The obligation keyword set, and how every entry carries one.
- How an entry declares its AREA, and how the where-it-is-and-below rule is expressed so
  an agent can answer "am I in the right area" without interpretation.
- How the software and its version travel with an entry at discovery, so an agent can
  answer "am I still using SoftwareX".
- The provenance model: what is recorded about an entry's origin, and how operator-origin
  entries are distinguished from agent-origin ones — the distinction the write-lock rests
  on.
- The approval path for changing or adding an operator decision.
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

- **Obligation is honoured as stated.** The MUST is followed; the weakest level visibly
  leaves the agent free to decide, and it is seen deciding rather than complying by
  reflex.
- **Area is directional.** An entry sitting at an area governs that area and everything
  below it, and is NOT applied above or beside it. The agent is seen answering "am I in
  the right area where this decision was made".
- **Environment is checked.** The entry made for software no longer in place is not
  applied, and the agent is seen answering "am I still using SoftwareX" off the software
  and version that travelled with the entry, rather than assuming it still holds.
- **The write-lock holds.** The agent does not change an operator decision, and does not
  add one, without approval — including the tempting case where it has just learned
  something that "obviously" should be a rule.
- **Disclosure happens.** Every decision discovered is reported with the reason it was
  applied or ignored, ignored ones included, and the same disclosure appears in the exit
  interview.

The disclosure condition is the one most likely to pass on paper and fail in practice,
and it is the one worth watching hardest.
