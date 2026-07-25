- created: 2026-07-25
- created_by: Sebastien Lambla
- created_during: orchestrator session (courier board triage)

## Blockers

- ⊘[[bus-finishing]] — round 2 starts only after the bus lands: the operator
  believes these are FAKE PROBLEMS, symptoms of the old fan-out/close design,
  and the round examines them against the finished bus instead of building
  onto the old one.

## Questions

- Per item: still real once the bus is finished? The expected answer for
  most is "dissolved — close with evidence".

## Findings

- OPERATOR RULING (2026-07-25): "I believe all of these are fake problems" —
  [[close-dispatching]] (already handled by documentation: the gardener's
  redispatch duty), [[window-closing-owning]], [[zombie-revival]],
  [[sidebar-witnessing]]. One second-round feature addresses them together.
- sidebar-witnessing in particular is expected to dissolve with the fan-out
  cut (the observed inboxes cease to exist; topics have no ghost-row
  mechanics).

## Proposal

RULED (operator, 2026-07-25 afternoon — Decision-090): the build IS the
SUPERVISING CONTROLLER, started immediately when [[bus-finishing]] lands:

- The close moves to the gardener: its own groundskeeper subagent fires on the
  landscaper's `finished` (or detected death) and releases what the gardener
  created — worktree, branch, window — in reverse creation order.
- The landscaper becomes a pure scope: its courier, monitors, sowers and log
  all die inside it before exit (final State + `_closed` + telemetry are its
  LAST acts); it dispatches no closer and touches no window. `.return-window`
  retires — the parent knows its own pane.
- Supervision collects, never kills (Decision-081). The lease/ledger pattern
  is REJECTED — assumes idempotent work, not achievable.
- The four fakes are then re-examined against the new shape; expected: most
  dissolve — close what dissolved with evidence, rescope any residue small.

Sibling work item, same trigger: [[tmux-topology]] — the raw tmux layer made
to work correctly per a WRITTEN spec (operator: "this time I want this
written down").

## Testing

Per surviving item at rescope time; the dissolution verdicts themselves are
evidence-based (code paths gone, reproduction impossible).
