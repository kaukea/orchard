- created: 2026-08-18
- created_by: fable-5 (operator report, naming round)

## Blockers

None.

## Questions

- What exactly fails — the description not matching real trigger phrasing, a
  missing/different frontmatter field, or the skill needing `compatibility`?
  Investigate before changing anything.

## Findings

Operator report (2026-08-18): the diagnostics skill's frontmatter is never
picked up by agents — the trigger does not fire, and the skill may require a
different frontmatter shape. Reported while renaming it to
diagnosing-issues; the rename does not fix the trigger.

## Proposal

Reproduce (a session with a broken thing, observe whether diagnosing-issues
loads), diagnose the trigger path, fix description or frontmatter
accordingly.

## Testing

To be agreed at build.
