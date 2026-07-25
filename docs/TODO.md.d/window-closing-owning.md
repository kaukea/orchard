# Window closing owning: agents close themselves; a listener kills at five

- created: 2026-07-22
- created_by: Sebastien Lambla

## Blockers

- None.

## Questions

- ~~Which agent is the designated killer?~~ RULED (operator, 2026-07-22,
  second 068 addendum): a subagent OWNED BY THE GARDENER, in its
  session — supervision lives where the fleet knowledge already is
  (announces, grace requests, dispatch ledger). Remaining HOW (reuse of the
  polish build's untested exit-grace code) is the build's to present.

## Findings

- Operator causality finding (2026-07-22): windows failed to close because
  the GROUNDSKEEPER deleted worktree files under agents still mid-teardown —
  the floor vanished beneath the closing agent. The groundskeeper charter now
  carries the hard precondition (never remove before on-closed); this task
  builds the mechanism proper.
- The sidebar-polish build already shipped exit-grace lifecycle code
  (evict-on-terminal-signal, grace tracking) — explicitly NOT live-tested,
  and recorded with a 10s default that Decision-068 corrects to FIVE
  seconds.

## Proposal

Per Decision-068 and its addendum: `on-closing` OPENS the agent's cleanup
phase — it tells its subagents to go, and each subagent tears down its OWN
monitors and resources (cascading self-cleanup). `on-closed` is emitted only
when the agent is ready to close its window. NOBODY observes the window
itself — supervision consumes signals about what agents are doing and
advertising, never tmux state; the window is an implementation detail. ONE
designated courier-listening agent watches on-closing/on-closed and kills any
agent exceeding its allocated time (five seconds default from on-closing;
longer only if requested at announce), broadcasting the death on its
behalf. The groundskeeper's worktree removal waits on `on-closed`/kill-
broadcast, already chartered. Sidebar eviction consumes the same signals
(already built).

## Testing

Live: a well-behaved agent closes cleanly inside five seconds — both
broadcasts observed, window gone, worktree removal proceeds only after
on-closed. A deliberately-hung agent is killed at five seconds, the death
broadcast lands, its sidebar row evicts, and the close completes. The
sidebar-polish build's untested exit-grace path gets its live pass here.

## Reframed by Decision-081 (2026-07-25)

Operator ruling: supervision kills are REMOVED — killing corrupts state and
hides bugs, so no agent ever kills another's process, pane, window, or
files. The kill-listener half of this task's premise (the five-second
killer, the kill-broadcast) is dead; what remains in scope is the first
half only — every agent closes ITSELF, and anything a dead agent leaves
behind is reported to the operator rather than reaped. Re-bloom against
Decision-081 before build.
