- created: 2026-07-25
- created_by: Sebastien Lambla
- created_during: orchestrator session (orchard-renaming close repair)
- completed: 2026-07-25
- completed_during: orchestrator session (procedural-on-main, Decision-065)

## Result

FIXED and proven (2026-07-25, commit 4530303): decision mirrors now carry the
`board` label (at create; retrofitted on match at each push), and `pull()`
also skips any `Decision-N:`-titled issue outright. Proof after a full mirror
push: local `pull` → 0 ingested; dispatched board-sync run 30157044393 →
success, `0 ingested`, no commit on remote main. Both filter sides shipped
(label + title), answering the open question as "both".

## Blockers

- None.

## Questions

- ~~Which side should filter: the cloud ingest workflow, the pusher, or
  both?~~ RESOLVED by the fix: both — label at the pusher, label+title skip
  at the puller.

## Findings

- Live failure, 2026-07-25 07:23 UTC: `board_gh.py push` created the decision-
  mirror issues (Decisions 057…067 among them); minutes later the callabloom
  board-ingest workflow read them as "GitHub-born changes", minted 7 task stubs
  (`decision-057…067` sidecars + TODO rows, gh#226–232) and committed straight to
  remote `main` (1c81106) — the board's own projection echoed back as intake.
  A projection→ingest feedback loop: every future push that mints decision
  issues can re-trigger it.
- Operator ruling at repair (2026-07-25): the 7 echoed stubs were KEPT for
  triage (merged, not dropped); the loop itself is this bug.
- Secondary damage: the echo commit sat on remote main while local main was
  unpushed, which is what the groundskeeper tripped over during the
  orchard-renaming close (see [[close-dispatching]] for that half).

## Proposal

Make the mirror/ingest pair loop-proof: decision mirrors (and any board-born
projection issue) must be identifiable as board-born — the ingest workflow skips
them; ideally the pusher also labels them so the skip is mechanical. Add a guard
test: a push followed by an ingest run produces zero new stubs.

## Testing

To agree when scoped — expected: run push (mints mirrors) then the ingest
workflow against the same repo state; ingest reports 0 ingested; no new sidecar
stubs appear.
