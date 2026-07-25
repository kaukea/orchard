# Step recording: one authored record, scripted projections

- created: 2026-07-22
- created_by: Sebastien Lambla

## Blockers

- None.

## Questions

- Record shape: which fields carry the judgment (subject, why-prose, test
  outcome, gitmoji, ruling-facts, ingest-increment prose) vs what the script
  derives (wrapping, trailers, file targets, timestamps)?
- Where the git-commit skill's format rules move: the script enforces them
  mechanically; the skill shrinks to the judgment guidance?

## Findings

- Operator principle (2026-07-22, extending Decision-056): data should not
  go through generation twice — a step's commit message, workstream-log
  entry, and ingest increment overlap ~70% and are each model-authored
  today (~600–900 output tokens per step across the three).

## Proposal

A step-record convention plus a small tool: the committing agent authors ONE
structured record per landed step; a script projects it into (a) the commit
message per the git-commit skill's format (subject/body/trailers assembled
mechanically), (b) the appended workstream-log entry, and (c) the
`ingest_increment` of the sower's typed return. Judgment is written once,
where the context is hot (Decision-056); assembly is deterministic. Free-form
log writing (deviations, findings, state) stays direct — only the per-step
landed entry is projected.

## Testing

One real build step recorded through the tool: the commit message passes the
git-commit skill's checklist, the log entry lands in the stream, the
increment reaches the landscaper's staged blocks — all from a single authored
record, none hand-written separately.
