- created: 2026-07-21
- created_by: Sebastien Lambla

## Blockers

- None.

## Questions

- ~~Where does the exit interview live?~~ Answered (operator, 2026-07-21): at the
  END OF THE SESSION — never by extending or resuming sessions to ask later, which
  re-materializes whole contexts purely for the interview. At session end the
  context is cache-warm (one short turn at read rates) and memory is freshest.
  Supporting mechanics: deviations are captured ROLLING in the stream log as they
  happen (handover discipline), so the interview is distillation, not recall; a
  session that dies abruptly leaves its rolling lines and the ingesting parent
  distills the note on its behalf (degraded — no reflection — and the miss itself
  is measurable telemetry). This also settles the anchor: the note lands on the
  session's final commit (the close commit for a landscaper; wherever the
  gardener was put to rest).
- ~~Archive home: the git folder is problematic for cloud hops — artifacts or a
  committed store?~~ Answered (2026-07-21): GIT NOTES on the close commit, under a
  dedicated ref (`refs/notes/telemetry`). The remote is the shared filesystem both
  sides already have; the report anchors to the exact commit it explains (squash
  locally, merge commit in cloud); the groundskeeper already pushes `refs/notes/*` at
  every close; notes pushes match no branch filters, so no workflows fire
  (Decision-033 honoured); retrieval is one `git fetch` + notes walk, batch by
  construction, one schema everywhere. Reports stay sanitized (rule-technical
  content only — the close gate already polices this).
- Anchor convention for sessions that do not produce a single commit (an
  gardener session spans many): last commit of the session, or a daily rollup
  note?
- Automatic rule changes: gated how? Operator word, statistical threshold, or
  structural provenance rules — an agent-written rule change is the sharpest case
  of "anything published will be used" (see the madmax provenance pattern,
  Decision-031).
- A/B unit: per-launch assignment of skill/prompt variants (kauk could deliver
  variants); what is the outcome measure per task type?
- Cadence: daily archive/optimization pass, or every N reports?

## Findings

- Operator concept (2026-07-21): telemetry here is ASKED, not observed — you do not
  get it by watching what the agent does, but by asking at the end: "What rules did
  you not follow, and why? How would you change them to be compliant?" Reports are
  archived on a daily/N cadence; prompts are optimized from them; improvement is
  measured STATISTICALLY over time and on specific tasks; changes are applied
  automatically, A/B tested, and reverted if they do not improve the curve.
- A rule with chronic deviations and a consistent "why" is a wrong rule, not a
  discipline problem — the reports write the diff.
- This is the measurement engine for Decision-027's question-economy direction:
  gates exist because of the error rate and shrink as upstream improves — this
  loop is what makes "the error rate improved" measurable rather than felt.
- Same-night specimens an exit interview would have caught and explained: the
  groom-vocabulary regression (sower rewrote from stale context), the PR #36
  session-shorthand prose (surfaced only because the operator read it), the
  session-naming plan dropping the declarative-mood rule (judgement half of a
  ruling had no build step to land in, so it evaporated).
- Thinking-vs-doing time and other observed measures remain computable by batch
  transcript mining (local transcripts are on disk; cloud needs an export step) —
  complementary to the asked telemetry, and the check on what goes unreported.

## Proposal

Iteration 1 — COLLECTION ONLY (operator, 2026-07-21: foundations before the
tower). Rolling `## Deviations` lines in every stream log; a three-question exit
interview at session end (rules not followed and why; how the rules would need to
change; the number one improvement that would have reduced token usage); the
report attached as a git note under `refs/notes/telemetry` on the session's final
commit; the close push widened to `refs/notes/*` so notes travel with every close,
local and cloud. After a couple of days of accumulated notes, the operator and
gardener read them by hand and decide iteration 2 from evidence.

DEFERRED (voluntary, to later iterations): analysis, statistics, prompt
optimization, A/B testing, automatic rule changes — the full loop as sketched in
Findings. Cloud emit wiring travels with the unlanded cloud-architect branch.

## Testing

To agree when bloomed — expected shape: a rule deliberately made slightly wrong
produces deviation reports whose optimization measurably reduces the deviation
rate without regressing task outcomes.
