- created: 2026-07-28
- created_by: Sebastien Lambla
- created_during: gardener

# A full review of the decisions register: what the rulings say, and how they are written

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

3. **How far does "how they are written" reach?** Two readings. The narrow one is
   conformance: the heading format, the mandatory timestamp, the mandatory keyword
   line, the supersession markers — all mechanically checkable against the spec in
   `AGENTS.files.md` §Decisions. The wide one adds prose quality: whether a body is
   written for a reader with no session context, in full sentences, with its jargon
   expanded, per the `writing` skill — which is a judgement call on 117 bodies.
   *Recommendation: both, but reported separately, because conformance findings are
   objective and prose findings are opinions and should not be mixed in one list.*

4. **Is the output a document, or tooling, or both?** A one-off review produces a
   findings document that is stale the moment the next decision is appended. A lint
   — the conformance half is entirely mechanical — keeps the register conformant
   forever and would fit beside the board lints that already exist. *Recommendation:
   the conformance half becomes a lint, the content half stays a document, because
   only one of the two can be automated honestly.*

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

A full review of `docs/decisions.md` along the two axes the operator named — what the
decisions say, and how they are written.

**The writing axis** covers conformance against `AGENTS.files.md` §Decisions: the
heading shape, the required timestamp, the required keyword line, the supersession
markers and their back-references, the chronological numbering, and the two-date
contract introduced by Decision-115. Every entry is checked and every deviation
reported with its entry number. Whether this axis also judges prose quality against
the `writing` skill is Question 3.

**The content axis** covers whether each entry is a ruling at all. Entries that record
a passing state, an interim limitation, or a fact about the code rather than a
deliberate choice are identified. So are pairs that contradict each other with no
supersession recorded between them, entries whose factual premises are no longer true,
and entries attributed to an operator ruling that the record does not support. Every
such finding is reported with evidence; none is acted on without the operator, per
Question 2.

Explicitly in scope: the register as a whole, all 117 entries, no sampling.

Explicitly NOT in scope: appending new decisions, deciding anything the register does
not already contain, and reconciling the register against the code to determine whether
a ruling was implemented. That last one is a much larger piece of work and would be its
own task.

## Testing

To be agreed with the operator before the build, and shaped by the answer to Question 4.

If the conformance half becomes a lint, its test is mechanical and unambiguous: the lint
runs over the current register and its findings are checked by hand against a sample of
entries chosen by the operator, including at least one known-good entry and several of
the eleven that are missing a timestamp. A lint that reports a defect where there is
none, or misses one that is there, fails.

If the output is a findings document, the test is the operator reading it against the
register — the honest method for a judgement deliverable, and the one that has to be
agreed rather than asserted, since no automated check can confirm that a review of
content is correct.
