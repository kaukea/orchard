- created: 2026-07-24
- created_by: fable-5

## Blockers

- None.

## Questions

- (none yet — the defect is fully characterised; modelling choice is plan
  work)

## Findings

- Measured in the writing-emails live run (psychometric-discovery close,
  merged eaa8bae): the v1 ordinal-index entropy SE proxy has a floor for
  multi-select/subset answers — both multi-select dimensions EXHAUSTED
  their item budgets instead of converging despite consistent answers
  (email-domain plateaued SE 0.901→0.888 over four rounds), dragging the
  overall band to "lower" by construction whenever multi-select dimensions
  dominate.

## Proposal

(to shape at bloom) A subset-posterior model for multi-select dimensions in
`tools/bloom_engine.py`, so consistent subset answers converge with an
honest SE instead of exhausting.

## Testing

To agree when scoped — expected: re-run a writing-emails-class round;
multi-select dimensions converge with consistent answers, and the overall
band is no longer floored by construction.
