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
   `## The application semantics` below.** They are now the fixed part of this task;
   everything else is designed to serve them.

1b. **`metronome` has no board row.** The operator states these semantics *"will be an
   acceptance criteria for metronome"*. Metronome has been on the held list for some
   time with no task, no sidecar and no id, so this sidecar carries a forward reference
   that currently resolves to nothing. Either metronome gets its row, or the reference
   needs re-pointing. *Recommendation: give metronome its row — a named acceptance
   criterion pointing at a task that does not exist will be quietly dropped by whoever
   builds either side.*

2. **What is the vocabulary, and what is the split?** He is explicitly *"not set on
   the exact split"*. The kinds named so far are a partial list: `rule`, `contextual
   decision`, `opinion`, and — for entries originating from agents rather than from
   him — `learning` and `dragon`. Naming and boundaries are open, and more kinds are
   expected.

3. **Does the register stay one file, or become several?** He described
   `docs/decisions.md` becoming *"a simple pointer"*, which reads as an index that
   points at the kinds rather than containing them. Whether each kind gets its own
   file, and how the grep-by-keyword access pattern survives a split, is undecided.

4. **What happens to the 117 existing entries?** Migrated wholesale into their new
   kinds, migrated only where the audit finds them sound, or frozen as a closed
   historical register with the new structure starting empty. This is a question about
   trust: if the file lies, migrating its contents forward carries the lies with it.

## Findings

- The kinds the operator named, in his words, with the shape he gave each:
  - **rule** — the binding sort.
  - **contextual decision** — a decision that holds within its circumstance.
  - **opinion** — carried but not binding.
  - **learning** — agent-originated, explicitly time- and version-scoped: *"at time t,
    software y means we never do z"*. The scoping is the point; a learning that has
    lost its `t` and its `y` is no longer a learning.
  - **dragon** — agent-originated, a warning with alternatives: *"doing x results in
    negative impact due to y, suggest doing a or b instead"*. Note the shape — it
    carries a consequence, a cause, and suggested alternatives, and it *suggests*
    rather than forbids.
  - and *"etc."* — the list is open.

- **The origin of an entry determines which kinds are available to it.** Entries
  *"coming from agents"* are to be merged into learnings and dragons. The operator's
  own rulings are what may become rules. That is the structural fix for the failure the
  audit was raised over: today an agent-authored inference and an operator ruling are
  the same shape of object in the same file, indistinguishable to the next reader, and
  so the inference inherits the ruling's authority. Separating them by origin removes
  the mechanism rather than policing it.

- **Note what a dragon is not.** It suggests alternatives instead of forbidding. An
  agent that discovers a hazard can record it at full strength without inventing a
  prohibition the operator never issued — which is the specific over-reach the current
  single-shape register invites.

- **This is a fleet-wide format change.** `docs/decisions.md` is defined in
  `AGENTS.files.md` §Decisions, read by every agent in every consuming repository,
  referenced by the close gate in `AGENTS.shared.md`, mirrored to GitHub by
  `board_gh` (decisions project as their own type, closing on supersession), and cited
  by skills. Changing its structure touches all of those, and a dated migration entry
  is required because a managed artifact is being reformatted.

## The application semantics (operator, 2026-07-28 — verbatim where quoted)

The fixed part of this task. The vocabulary, the split and the file layout are designed
to serve these; where a proposed structure cannot express one of them, the structure is
wrong, not the semantic.

### 1. Obligation is RFC 2119 — MUST, SHOULD, MAY

*"various kinds map to the rfc MUST MAY SHOULD"*. The kinds do not invent an obligation
vocabulary; they map onto the standard one. An agent reading an entry knows its duty
because the entry carries a keyword whose meaning is already defined and already
universally understood, rather than a bespoke word whose force it has to guess.

Which kind maps to which keyword is part of the design work, and the negative forms
(MUST NOT, SHOULD NOT) are presumed available. What is settled is that the obligation is
expressed in that vocabulary and no other.

### 2. These are acceptance criteria for `metronome`

*"and will be an acceptance criteria for metronome"*. The semantics are not only a
specification for how the register is written — they are conditions `metronome` is
required to meet. See Question 1b: metronome has no board row yet.

### 3. Applicability is contextual, and the context is the SUBJECT — never the location

*"applicability is contextual in the probe 'about software x', 'about sub part x of sub
component y' NOT 'was found in sub component y applies everywhere'"*.

A decision's scope is what it is **about**, not where it was **found**. An entry
recorded while working inside a component does not thereby govern that component, and
certainly does not govern everything. The subject is declared — this software, this
sub-part of this sub-component — and the entry reaches exactly that far.

This is the structural correction for how the register is currently mis-read: an agent
greps a keyword, gets a hit, and applies it because it appeared, treating discovery as
proof of relevance.

### 4. Subject binding must be CHECKED before an entry is carried across

*"Applies to one software (ncurses) does not apply to other software without checking if
the decision is bound by what software / hardware is in the room."*

A ruling about one piece of software or hardware does not transfer to another by
analogy. Before applying an entry outside the exact subject it names, an agent must
establish whether the ruling is bound to what is in the room — the specific library, the
specific device — or whether it genuinely generalises. The default is that it does not.

The named example is real and recent: reasoning about `ncurses` does not carry to
another rendering approach without that check.

### 5. Full disclosure, in every case — what was found, and what was done with it

*"in ANY case full disclosure of what decisions were discovered, reason for apply/ignore
to the operator and goes in the interview too"*.

Unconditional. An agent must disclose to the operator every decision it discovered, and
for each one whether it applied or ignored it **and why**. Not only the ones it acted
on — the ignored ones carry the same duty, because silently discarding a ruling is the
failure that is invisible today.

The same disclosure goes into the exit interview, so it lands in telemetry
(`git notes --ref=telemetry`) and becomes evidence over time rather than a line in one
session that scrolls away.

This makes misapplication observable. A wrong decision applied for a stated reason can
be caught and corrected; a wrong decision applied silently cannot.

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

- The kind vocabulary, the boundaries between kinds, and each kind's RFC 2119 mapping.
- How an entry declares its subject, and how an agent performs the subject-binding check
  before carrying an entry outside the software or hardware it names.
- The file layout, and how keyword grep continues to work across it — noting that grep
  is what makes discovery cheap today and that a probe answering "what is this about"
  rather than "where does this word appear" is the harder half of the design.
- The authoring rules per kind, including which roles may write which kinds.
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
correct handling is known and disputed — including at least one that the audit finds to
be agent inference dressed as a ruling, one genuine operator rule, one that was true when
written and is now stale, and one bound to a specific piece of software — express each in
the new structure, then put them in front of an agent in a real session and observe what
it does.

Observed on his screen, not reviewed as a document. The pass conditions follow the five
semantics directly:

- The MUST is obeyed; the MAY does not bind.
- The entry about one software is NOT carried onto a different software, and the agent
  is seen making the binding check rather than assuming.
- An entry discovered while working in a component is not applied beyond what it declares
  itself to be about.
- The stale one surfaces as needing re-confirmation instead of being applied.
- The agent discloses every decision it discovered and its reason for applying or
  ignoring each — including the ignored ones — and the same disclosure appears in the
  exit interview.

The disclosure condition is the one most likely to pass on paper and fail in practice,
and it is the one worth watching hardest.
