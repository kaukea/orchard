- created: 2026-07-24
- created_by: Sebastien Lambla

## Blockers

- Builds on the bloomer v1 engine ([[psychometric-discovery]], on
  f/psychometric-discovery, close pending at time of boarding).

## Questions

- Block surfacing: within one block, is each item still its own choice
  popup answered in sequence from the same pane (operator's stated
  preference), or one composite form?
- Do consistency probes stay disguised in the FINAL report too, or does the
  report reveal which items were cross-checks once the round is over?
- Item-novelty threshold: minimum expected information gain per administered
  item — engine parameter to agree at plan time.

## Findings

- Operator critique (2026-07-24, after the writing-emails live run): the
  round-by-round administration is extremely wasteful — psychometric tests
  group many questions so the respondent answers them one at a time from the
  same tab, saving tokens and operator time. He was probed five times on
  near-identical cloud-agents-and-email ground.
- Analysis (orchestrator, same day): one-item-at-a-time is NOT required by
  the machinery. Multistage testing (block → score → route, the GRE's model)
  keeps all but a few percent of pure-CAT efficiency; and with several
  largely independent dimensions, cross-axis adaptivity is weak — a block of
  one probe per open dimension per round loses almost nothing. The five
  repeats were the multi-select SE-floor defect re-probing an exhausted
  dimension, which batching alone would not fix: the engine also needs an
  item-novelty constraint (no probe below an information-gain threshold, no
  near-duplicate items).
- Operator critique 2 — BLINDING: a psychometric instrument must not
  announce the axis it is measuring; v1 printed the dimension topic on every
  probe. Naming the construct invites demand effects and defeats person-fit
  consistency checks (cross-checks only detect inconsistency when they are
  not visible as cross-checks). Fix: neutral phrasing, no dimension labels,
  disguised consistency probes, axes revealed only in the final report.

## Proposal

(to shape at bloom) Block-adaptive administration for the bloom engine: one
probe per open dimension per block, answered sequentially from one pane
pass; engine updates all posteriors between blocks; item-novelty constraint;
blind items throughout, axes visible only in the convergence report.

## Testing

To agree when scoped — expected: re-run a real bloom round; the operator
confirms the round count collapses (target: ≤4 blocks for a
writing-emails-sized task), no near-duplicate probes appear, and no probe
names its axis.
