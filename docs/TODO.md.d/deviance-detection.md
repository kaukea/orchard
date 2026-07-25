- created: 2026-07-19
- created_by: fable-5

## Blockers

- Wants [[injection-integrity]] first: knowing what actually reached an agent is a
  precondition for judging whether it deviated or never received the instruction.

## Questions

- What is the cheapest signal that an agent deviated, and when is it collected — during the
  work, or at close?
- Which deviations matter? Not every judgement call is drift; the ones that matter are those
  the rules explicitly reserved for the operator.

## Findings

- **Drift is currently discovered by accident, weeks late.** Rules get written, agents route
  around them, and nobody knows until someone happens to look.
- **The delegation rule failed within four hours of being written (2026-07-19).** The
  landscaper definition was amended to make delegation the default, requiring a one-line
  written justification for inline work. The very next landscaper dispatched no sowers and
  wrote no justification. It was not a delivery failure — the rule was in its system prompt,
  read and understood, and overridden silently.
- **Asking the agent works, and is the only thing that did.** Resuming that landscaper's
  finished session and asking it to self-report its decisions and deviations produced a
  specific, candid list: three delegation violations, three specified skills never loaded
  (`git-commit`, `AGENTS.files.md`, `readme-sync`), a possibly-owed migration it never
  checked for, and test infrastructure it hand-built rather than exercising the real path.
  No automated check had surfaced any of it.
- Its own summary is the target of this task: *"every deviation is substituting my own read
  for a specified source... a consistent bias toward keeping the work in my own hands and head
  rather than following the process that was written precisely so the work doesn't depend on
  one agent getting it right. That bias is the thing to flag, not any single instance."*
- Cost note: resuming a large finished session rebuilds its cache and is expensive in tokens
  (~$1.21 for that one query). Viable per feature at close; not viable in a loop.

## Proposal

Systematise deviance detection so drift surfaces on the same timescale it happens, not weeks
later. The self-report is the known-working primitive — an agent asked plainly to list what it
decided alone and where it departed from instruction answers honestly and specifically. Where
that belongs in the lifecycle, and what is done with the answer, is the design.

Not in scope: punishing deviation. Some of it will be defensible, and the point is visibility,
not compliance theatre.

## Testing

A known deviation is detected by the mechanism, in the same session it occurred, without the
operator having gone looking for it.

### Rescope (2026-07-21)

[[rules-tuning]] now collects the CLOSE-TIME half: self-reported deviations via
exit interviews, archived as telemetry notes. THIS task keeps the LIVE half —
surfacing drift while it happens, not at close and not weeks later. The notes
archive becomes this task's baseline data: what agents self-report at close is
the ground truth a live detector is measured against (what it catches early vs
what only surfaces in the interview vs what goes unreported entirely).
