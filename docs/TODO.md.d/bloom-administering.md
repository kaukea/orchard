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
- Repeat-probe policy: deliberate re-probing is legitimate instrument
  machinery (consistency checks, reliability triangulation) — so what
  separates justified repeats from the wasteful kind seen in the live run,
  and what bounds them? (Gardener's UNCONFIRMED suggestion, needing
  operator confirmation at scope: an expected-information-gain floor per
  administered item.)

## Findings

- Operator critique (2026-07-24, after the writing-emails live run): the
  round-by-round administration is extremely wasteful — psychometric tests
  group many questions so the respondent answers them one at a time from the
  same tab, saving tokens and operator time. He was probed five times on
  near-identical cloud-agents-and-email ground.
- Analysis (gardener, same day): one-item-at-a-time is NOT required by
  the machinery. Multistage testing (block → score → route, the GRE's model)
  keeps all but a few percent of pure-CAT efficiency; and with several
  largely independent dimensions, cross-axis adaptivity is weak — a block of
  one probe per open dimension per round loses almost nothing. The five
  repeats were the multi-select SE-floor defect re-probing an exhausted
  dimension — they were wasteful because they could no longer move the
  posterior, not because repetition is wrong per se.
- OPERATOR CORRECTION (2026-07-24, same evening): the five-probes complaint
  was about wasted time, NOT a ruling banning duplicate probes — no such
  decision was requested or confirmed. An earlier version of this sidecar
  (and its boarding commit, ecacd5c) overstated it as a "no near-duplicate
  probes" constraint; that constraint is WITHDRAWN and survives only as the
  unconfirmed suggestion in Questions. Deliberate re-probing remains
  available to the instrument — the blinding fix's disguised consistency
  checks depend on it.
- Operator critique 2 — BLINDING: a psychometric instrument must not
  announce the axis it is measuring; v1 printed the dimension topic on every
  probe. Naming the construct invites demand effects and defeats person-fit
  consistency checks (cross-checks only detect inconsistency when they are
  not visible as cross-checks). Fix: neutral phrasing, no dimension labels,
  disguised consistency probes, axes revealed only in the final report.

## Proposal

(to shape at bloom) Block-adaptive administration for the bloom engine: one
probe per open dimension per block, answered sequentially from one pane
pass; engine updates all posteriors between blocks; blind items throughout,
axes visible only in the convergence report. Repeat-probe policy per the
open Question above.

## Testing

To agree when scoped — expected: re-run a real bloom round; the operator
confirms the round count collapses (target: ≤4 blocks for a
writing-emails-sized task) and no probe names its axis.
