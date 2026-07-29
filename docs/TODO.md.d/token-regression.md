- created: 2026-07-29
- created_by: gardener
- created_during: main

# Token regression: a fixed scenario, telemetry from both sides, an alert when it gets worse

## Proposal

**Operator ruling, 2026-07-29, verbatim:** *"A/B is a good test to pass today, the feature
we need is token regression: Same scenario implementation, collect telemetry from
messaging and from claude and timings and alert when there is regression"*.

An A/B measurement proves one change was an improvement. It does not stop the next change
undoing it — which is the failure this repository keeps living: work lands, is measured,
and is quietly reverted or re-inflated with nobody noticing for days.

What it is:

- **A fixed scenario**, implemented once and run repeatedly, so runs are comparable.
- **Telemetry from the messaging layer** — what the courier moved and what it cost.
- **Telemetry from Claude** — tokens in and out for the run.
- **Timings.**
- **An ALERT when there is a regression.** The alert is the feature. Collection without
  alerting is a dashboard nobody reads.

## Findings

- The measurements this needs are the same ones the sidebar consumes (time, tokens in and
  out, context remaining, model and effort) — the script already detects them without a
  model involved. This task is the harness and the alerting around them, not new
  instrumentation from scratch.
- The cost being defended: ~3,000 tokens per message delivered, with a 4,023-word agent
  definition re-read by every agent in every session before a byte moves.

## Questions

- **What is the fixed scenario?** It has to be representative enough to catch a real
  regression and cheap enough to run often.
- **What is a regression** — any increase, a percentage band, or a threshold the operator
  sets?
- **Where does the alert go**, and who is expected to act on it?
- **When does it run** — every close, on demand, or on a schedule?

## Testing

To agree at scope. Expected shape: deliberately introduce a known regression and watch the
harness catch it, rather than only observing a green run on unchanged code.
