- created: 2026-08-19
- created_by: gh-ingest
- created_during: interactive

## Blockers
- None known yet.

## Questions
- Ingested from GitHub issue #303 — needs triage: type, component,
  urgency, scope.

## Findings
- Filed on GitHub (https://github.com/kaukea/orchard/issues/303); original body preserved below.

Full report from the kauk gardener, written for this repository's gardener to integrate into the board after synchronization. The kauk run exercised the whole orchard machinery end to end — two features through bloom, launch, supervision, close and ingest — and everything below is what belongs here rather than in kauk. Items already filed as issues are referenced, not restated.

## Already filed, awaiting triage

- #300 — the supervision contract: one beekeeper report per feature at resolution; operator gate-waiting never reported; model/effort sizing is the gardener's call stated in passing; no per-tick messages from any agent.
- #301 — a gardener session's end loses live state; operator rulings recorded there verbatim: the gardener's window never closes, and the lease/liveness mechanism belongs to the beekeeper alone. Design is the feature's, with the operator.
- #302 — readiness phases are inadequate; the bloomer, the gardener's triage, and the §TODO stage vocabulary need rewriting.

## Fixes already landed on this repository's main during the run

- beekeeper.md frontmatter flattened (00e06ac): a multi-line frontmatter value silently drops the agent from Claude's registry — the beekeeper was unlaunchable and the failure was silent.
- dispatch-agent.sh (09c76cf and f8d0395): prompt quoting via printf %q (an apostrophe used to kill the pane before Claude started), and window targeting anchored to the caller's $TMUX_PANE (it used to follow the operator's focused window — the standing cause of layout mis-renders).
- Root deliverables moved into files/ (6733c8c) and later corrected: hooks now expose via the package format, not a shipped settings.json (d8f21f1); dispatch passes kai's static settings file (5fbcbca).

## Defects observed, not yet fixed here

1. Multi-line frontmatter values remain in bloomer, gardener, landscaper, and sower definitions. They register today, but the beekeeper case proves the shape can silently unregister an agent. Flatten them; consider a lint so an edit cannot reintroduce it.
2. pane-promote.sh resolves the client's active pane instead of the caller's ($TMUX_PANE ignored) — self-promotion can grab the wrong pane. Same class as the dispatcher bug already fixed.
3. The courier definition's watch polls: it woke its parent roughly every seventy seconds across fifty idle ticks despite instructions to block, and kept cycling even after acknowledging its own release — it had to be force-stopped. The fix needs a continuously-alive wait, not a stop-and-rearm loop.
4. bloomer-launch.sh bypasses dispatch-agent.sh (a board task for this was already created during the run: f03bab6).
5. The beekeeper died silently twice in one run — once at the session boundary, once unexplained mid-afternoon with its pipeline still active. #301's design should treat repeated silent beekeeper death as the primary case, not the edge.
6. The tmux layout contract (one window per feature; auxiliary panes stacked in the right column) is the operator's repeated correction and should be enforced by the dispatch tooling itself, not by hand-moving panes.

## Operator rulings and orders that create orchard work

- The landscaper agent definition needs a complete rewrite (operator order, recorded at the fleet-settings gate on 2026-08-19).
- The gardener launch: kauk ships only a GENERIC agent-launcher skill (/kai agent <agentname> if that syntax is supported) that launches an existing agent with kai's settings; ORCHARD wraps it to launch the gardener from its own agents. The wrapper skill is a new orchard deliverable (operator judgement, 2026-08-19).
- Valve exists only on the unmerged f/decision-making branch, so every pipeline runs without the judging role — merging or superseding it needs a decision.
- migrations-pending.sh and the AGENTS.files.md §Migrations text still carry the retired agent-applies model; the replacement §Migrations text is ready in kauk's docs/package-format.md, and the hook's rewrite design (deliver only outstanding ask files, stay silent otherwise) is recorded on kauk's migration-asks-lifecycle task. The files are this repository's, so the work lands here.

## Observations for the record

- An idle session named "kauk ▸ migrations-at-sync" appeared hours after that feature closed, launcher unknown; the operator was told and it was left untouched.
- The readiness evidence, the supervision-contract failures, and the session-boundary losses all come from the same two-day run and are internally consistent; the kauk board carries the kauk-side halves (courier-blocking-watch, tmux-layout-contract, migration-asks-lifecycle, estate-links-run).
