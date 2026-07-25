# Sidebar witnessing: the ephemeral-courier observer gap

- created: 2026-07-23
- created_by: fable-5

## Blockers

None.

## Questions

(none yet — unbloomed)

## Findings

- The sidebar model's only data source is the courier spool: unconsumed message
  files on disk plus traffic it happens to witness while watching
  (`tools/sidebar_model.py` docstring names the accumulation problem itself).
  Three symptoms follow, all observed live on 2026-07-23:
- **Ghost rows.** Six dead session folders in orchids' spool (the whole of
  yesterday's fleet — sessions ended without terminal signals when the day
  closed) rendered as live "Done, awaiting" rows in every fleet sidebar,
  with no eviction possible: the terminal signal that evicts a row can
  never arrive from a dead sender.
- **Invisible living agents.** The genuinely live SignMc seal-chain
  landscaper and both gardeners showed nowhere: their announces predated
  the sidebar processes and were consumed by live recipients, so a
  late-starting observer never sees them.
- **Zero-peer repos are unwitnessable.** `bus.py fan_out` writes only into
  peer session folders; with one live session in a repo a broadcast reaches
  0 folders and touches no disk at all — proven: after the spool cleanup,
  the orchids gardener's activity broadcast reported "broadcast to
  0 agents". A single-agent repo can never surface on the sidebar.
- Remediation applied same day (hygiene, not the fix): dead spool folders
  archived to `.git/the-works/_ingested/bus-spool-20260723/`, both sidebar
  panes restarted clean.
- Re-observed after the 2026-07-24 ~14:07 tmux crash (pane capture, evening):
  the sidebar showed THREE near-identical rows for the one feature — the
  crashed landscaper (dead ~5h), the bloomer test session (exited cleanly
  hours prior, ⚪ row), and the live successor — indistinguishable because
  every row renders the same truncated board title. The courier itself also
  still carried the two dead sessions as registered and one orphaned
  sower as live.

## Proposal

The sidebar must render the fleet truthfully regardless of when its own
process started: agents that are dead never render; agents that are alive
always render — including in single-agent repos and when they have been
silent since the watcher started. Scope is the observer's data source /
courier contract, not a courier rewrite. Boundaries with neighbours:
`bus-singleton` reaps stray sidecar folders; exit-grace enforcement
(sidebar-polish item 2) covers a signalling agent that outlives its grace;
this task covers what the OBSERVER can know.

## Testing

- Kill an agent session with no terminal signal → a freshly started sidebar
  must not render it.
- Start the sidebar after an agent announced → the agent still renders.
- One live agent alone in a repo → its activity reaches the repo header.
