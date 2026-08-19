- created: 2026-08-19
- created_by: gh-ingest
- created_during: interactive

## Blockers
- None known yet.

## Questions
- Ingested from GitHub issue #302 — needs triage: type, component,
  urgency, scope.

## Findings
- Filed on GitHub (https://github.com/kaukea/orchard/issues/302); original body preserved below.

Operator order (2026-08-19, kauk run): the readiness phases are wholly inadequate if they exist at all anymore, and the agents serving them need rewriting.

Evidence from the two-day kauk run, where the pipeline was exercised end to end:

- The badge predicted nothing. Every "plan-ready" task still went through a full live scope round with the operator at launch — the mandatory pre-launch bloom re-derived the WHAT each time, so the stage carried no load. Meanwhile tasks the pipeline showed as untouched ("todo · plan-ready") were in fact half-shipped in the code (the categories rename and the dependency closure had landed in the reader weeks of board-time earlier), and the operator had to correct the board from his own memory.
- Stages churned without meaning. One bug moved blocked-on-answers → plan-ready → rescoped → plan-ready within hours as rulings landed in conversation; the stage was always a lagging echo of the transcript, never a source of truth.
- The bloom round reports pseudo-measurement. The Decision-050 round returned "converged with overall SE 0.68, band lower" with self-admitted uncalibrated, LLM-assumed item parameters — numbers that look like psychometrics and inform nothing.
- The projection rule (stage derived from the sidecar, board never opened in steady state) drifted immediately: badges disagreed with sidecar reality in both directions and only a human noticed.

What this asks for: a rewrite of the readiness model and of the agents that read and write it — the bloomer above all, plus the gardener's triage and the §TODO stage vocabulary — so that whatever replaces the phases states something that is actually true at launch time and is cheap to keep true. Whether that is fewer stages, no stages, or a different signal entirely is the feature's design call, made with the operator.

Related: the supervision-contract intake (#300) and the session-boundary losses (#301) came out of the same run.
