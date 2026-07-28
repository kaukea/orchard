- created: 2026-07-28
- created_by: Sebastien Lambla
- created_during: gardener

# The decisions register lies: audit every entry for truth, provenance and authority

## Blockers

None. The register is a committed document and the review reads it in place; no
dependency, no capability gap, no other task holds it.

## Questions

1. **Does this review REPORT, or does it also FIX?** The two are very different
   pieces of work. A report is a findings document listing every entry that is
   malformed, stale, contradicted, or not actually a ruling, and it leaves
   `docs/decisions.md` untouched. A fix pass rewrites the register — restoring
   missing timestamps, striking entries that were superseded only in prose,
   demoting entries that record a state rather than a ruling, and rewriting bodies
   that read as session shorthand. *Recommendation: report first, fix second, as
   two rounds.* The register is the fleet's constitutional record and every agent
   greps it; a single pass that both judges and edits gives no point at which the
   judgement can be reviewed before it is applied.

2. **Who arbitrates a ruling that looks wrong?** The review will find entries whose
   content is questionable — a claim about the code that was never true, a ruling
   that the operator never actually made, a ruling now contradicted by what shipped.
   None of those can be corrected by an agent on its own authority, because the
   register's whole value is that it records the operator's decisions and not an
   agent's reconstruction of them. *Recommendation: the review MARKS such entries
   and proposes a disposition, and the operator rules on each; no entry is struck,
   rewritten, or demoted without him.*

3. ~~How far does "how they are written" reach?~~ **ANSWERED — and the axis was
   the wrong one.** The question offered prose quality. The operator replaced it
   with provenance and legitimacy, in his words: *"Who wrote them, under what
   circumstance, was the operator asked at all, is it inference, is it situational
   or global, does it even belong there"* — and immediately added that this is a
   ***"non exhaustive list"***. It is a demonstration of the kind of interrogation
   the register must survive, not the checklist to run against it. See `## Proposal`,
   second axis. Prose quality is not part of this task.

4. ~~Is the output a document, or tooling, or both?~~ **ANSWERED — a findings
   document only, and no lint.** The operator's reason matters more than the answer:
   he intends to *"change the structure of decisions completely to avoid any
   recurrence"*. Building a lint against the current structure would be building
   tooling for a format that is about to be replaced. This audit is therefore an
   INPUT to that restructure — it establishes what is actually in the register and
   where each entry came from, so the new structure is designed against the real
   contents rather than against an assumption about them. The restructure itself is
   a separate task, `decisions-restructuring`.

## Findings

Measured on `docs/decisions.md` at `5c1ccf5`, 2026-07-28. These are the grounds for
the task, not the review itself.

- **Size:** 117 entries over 2093 lines, spanning Decision-001 (2026-07-16) to
  Decision-115 (2026-07-27). Twelve days. The register is young and already large
  enough that nobody reads it whole — which is by design, it is grepped by keyword,
  and which is also why defects in it survive unnoticed.

- **Eleven entries carry a date with no time**, in the form `[2026-07-16]` rather
  than `[2026-07-16 11:02 CEST]`. The format spec makes the time REQUIRED and gives
  two reasons: it disambiguates decisions made on the same day, and it feeds the
  staleness rule by which an old decision is treated as provisional and re-confirmed
  rather than assumed current. Eleven entries are therefore undatable to the hour and
  cannot be ordered against a same-day sibling.

- **Supersession is described in prose far more often than it is marked.** Exactly
  one heading in the file is struck through, yet twenty-five lines mention
  supersession. The register's documented reading order depends on the marker: a
  reader greps a keyword, reads the hits oldest to newest, and is meant to meet the
  strike-through before reaching the entry that replaced it. Where supersession lives
  only in the body of the newer entry, that protection does not operate, and a grep
  can surface a dead ruling as though it were live.

- **Decision-115, appended 2026-07-27, changed the heading contract** — a decision
  now carries two dates, when it was ruled and when it was last confirmed. The 114
  entries that precede it do not carry the second date, so the newest rule in the
  register is honoured by one entry in it.

- **The register's own content rule is that a decision is a ruling and never a
  state**, and that a fact about what the code currently does must not be recorded
  as a decision because a later reader will mis-read it as a ruling and act on it.
  That failure has already happened in this repository within the last two days: an
  agent staged a decision entry asserting that a colour path was broken and that the
  machinery around it was accidental complexity. Neither claim was true — the
  machinery was the operator's deliberate downgrade ladder — and a later agent
  inherited the framing from the staged entry and repeated it, proposing the deletion
  of working code. The entry was amended before it reached the register. Nothing
  would have caught it if it had not been.

- **The register documents an idiosyncrasy check that nothing performs.** The spec
  says that when a keyword grep surfaces two live decisions that contradict each other
  with no recorded supersession, the operator is to be warned and asked which is
  current. That is a description of what an agent should notice in passing, not a
  check anything runs, and no pass over the register has ever been made to find such
  pairs deliberately.

## Proposal

A full review of `docs/decisions.md`. The operator's premise, in his words, is that
**"the file lies"**. That is the frame for the whole task: this is not a tidy-up of a
basically-sound document, it is an audit of a record suspected of asserting things that
are not true. The review's job is to find out where, how much, and how it happened.

The register's authority rests entirely on one claim — that it records decisions the
operator made. Every agent in the fleet greps it and honours what it finds without
question, because that is what it is for. An entry that is inference, generalisation,
or invention therefore does not sit inertly in a file; it propagates as a ruling, and
it has already licensed at least one agent to act against the operator's intent.

### Axis one: does the entry say something true and current

Whether each entry is a ruling at all. Entries recording a passing state, an interim
limitation, or a fact about what the code did at the time rather than a deliberate
choice — which the register's own spec forbids. Pairs that contradict each other with
no supersession recorded between them. Entries whose factual premises were wrong when
written or have since become wrong. Rulings contradicted by what actually shipped.

### Axis two: is the entry legitimate — provenance and authority

The operator's line of interrogation, given as a **non-exhaustive** demonstration and
to be extended by the reviewer rather than treated as a checklist:

- **Who wrote it** — which agent, which model, which role.
- **Under what circumstance** — mid-build, at a close, staged by a landscaper, folded
  by a groundskeeper, or written by the operator himself.
- **Was the operator asked at all** — is there evidence of a question put and answered,
  or does the entry simply assert a ruling with nothing behind it.
- **Is it inference** — did an agent generalise a passing remark, a complaint, or an
  offhand preference into a standing constraint. This is the known failure: an entry
  currently staged on another branch exists precisely to strike a rule that "was never
  a ruling, just a one-line remark generalised by an agent".
- **Is it situational or global** — was a decision correct for one circumstance written
  as though it binds everywhere and forever.
- **Does it even belong there** — is this a decision, or something that should have been
  a changelog line, a code comment, or a task.

Authorship and circumstance are recoverable from git without judgement: each heading
traces to the commit that introduced it, and that commit to its branch, feature and
author. That makes a large part of this axis mechanical evidence rather than opinion,
and it is what the review builds its judgements on top of.

The reviewer is expected to find grounds the operator did not list. The six above are
the shape of the suspicion, not its boundary.

### Scope

In scope: the register as a whole, all 117 entries, no sampling. Conformance against
`AGENTS.files.md` §Decisions — heading shape, required timestamp, required keyword
line, supersession markers and back-references, chronological numbering, the two-date
contract from Decision-115 — is checked as part of the pass, but it is the least of it.

NOT in scope: appending new decisions; deciding anything the register does not already
contain; prose quality against the `writing` skill; and a full reconciliation of every
ruling against the code to determine whether it was implemented, which is a much larger
piece of work and would be its own task.

Nothing is struck, demoted or rewritten on an agent's authority beyond the objectively
mechanical, per Question 2.

## Testing

The deliverable is a judgement document, so the test is the operator reading it against
the register. That has to be stated plainly rather than dressed up: no automated check
can confirm that a verdict on an entry's legitimacy is correct, and claiming otherwise
would be exactly the kind of false assurance this task exists to find.

What CAN be checked mechanically, and must be, before it reaches him:

- **Coverage is total.** All 117 entries appear in the findings, none skipped. A count
  against the register proves it.
- **Every provenance claim resolves.** Each entry's stated author, commit, branch and
  feature is checkable against git; a spot-check of entries chosen by the operator must
  match. A provenance table that is itself unreliable would be the same failure one
  level up.
- **Every verdict cites its evidence.** No entry is called inference, over-generalised,
  or misplaced without a pointer to what makes it so — the commit, the absence of any
  recorded question, the contradicting entry. A verdict with no evidence is an opinion
  wearing an audit's clothes.

The operator then reads the findings. The sample he checks is his to choose, and the
review must not pre-select it.
