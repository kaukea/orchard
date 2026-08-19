- created: 2026-08-19
- created_by: gh-ingest
- created_during: interactive

## Blockers
- None known yet.

## Questions
- Ingested from GitHub issue #301 — needs triage: type, component,
  urgency, scope.

## Findings
- Filed on GitHub (https://github.com/kaukea/orchard/issues/301); original body preserved below.

Observed live across the 2026-08-18/19 kauk run, when the gardener session ended mid-flight and a successor booted the next morning. The durable board reconstitutes fine; what does not survive is everything session-scoped, and the successor has to rediscover it by accident or not at all:

1. Armed watches die silently. The GitHub Actions failure monitor ends with the session; no durable record says it existed, so the successor only re-arms it if the charter text reminds it to. Any wakeup or watch the gardener had running is in the same position.

2. The courier dies with the session. Until the successor spawns a new one it is invisible to peers and silently misses broadcasts — including resolution reports beekeepers may have sent into the gap.

3. Expected results are not recorded anywhere durable. "A report is due from the fleet-settings-wiring beekeeper" lived only in the dead session's conversation; the successor inferred it from an open worktree and an open stream. Beekeepers and landscapers that died across the boundary leave no structural trace of what was still owed.

4. Ingest debt piles on the boundary. A feature that closed as the session ended left board badges unflipped, the changelog entry staged, the stream unarchived — the successor had to detect and finish all of it cold.

5. Operator questions raised mid-run survive only in transcripts. The probe-window question and the SignMc debris call outlived the session only because another agent's workstream log happened to mention them.

Direction to consider (the feature owns the design): the gardener writes a small durable register as it dispatches and arms things — expected results, armed watches, open operator questions — and the boot checklist replays it. Relates to the summon-restarting work already on this board.
