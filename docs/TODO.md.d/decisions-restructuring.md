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

1. **What are the application semantics?** This is the one thing the operator is
   *"absolutely set on"* — how agents are to apply decisions when they work — and it
   is not yet written down anywhere. It is the specification this whole task serves;
   the vocabulary and the split are downstream of it. It needs to be captured from him
   verbatim before anything is designed, not inferred from the kinds he named.

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

## Proposal

Replace the single flat decisions register with a structure that distinguishes kinds of
recorded knowledge, and — the actual point — define how an agent is to apply each kind
when it works.

The operator's framing: `docs/decisions.md` becomes *"a simple pointer"* to a rule, a
contextual decision, and an opinion; entries originating from agents are merged into
learnings, dragons, and further kinds to be named. He is not set on the exact split. He
is absolutely set on the application semantics.

**The application semantics are the deliverable.** Vocabulary and file layout are
consequences of them, not the other way round, and the task must be built in that order
or it will produce a pleasant taxonomy that changes nothing about agent behaviour. For
each kind the specification must state, unambiguously and in terms an agent can act on:
what obligation it carries; whether an agent may depart from it and what it must do if
it does; what makes it expire or require re-confirmation; who may author it; and what
an agent must do on encountering two of them in conflict.

The reason the current register fails is not that it is untidy. It is that every entry
in it carries the same implied obligation — binding, permanent, universal, operator-
issued — regardless of whether any of that is true of it. A structure that records what
an entry actually *is* removes the failure at its source.

### In scope

- The application semantics, captured from the operator and written as specification.
- The kind vocabulary and the boundaries between kinds.
- The file layout, and how keyword grep continues to work across it.
- The authoring rules per kind, including which roles may write which kinds.
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
be agent inference dressed as a ruling, one genuine operator rule, and one that was true
when written and is now stale — express each in the new structure, and then put them in
front of an agent in a real session and observe what it does. The rule must be obeyed,
the inference must not bind, and the stale one must surface as needing re-confirmation
rather than being applied. Observed behaviour on his screen, not a document review.
