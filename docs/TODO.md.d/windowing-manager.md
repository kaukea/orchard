- created: 2026-07-29
- created_by: gardener
- created_during: main

# Windowing manager: it receives delegations, and it closes what it opened

## Proposal

**Operator ruling, 2026-07-29, verbatim:** *"It needs synchronisation between the
supervisor, and a windowing manager (currently tmux) that gets the delegations, so other
window managers can be implemented (it was a feature i was to be working on today)"*.

This is Decision-114's placement component, made concrete and named. It is the piece that
makes "there should not be a landscaper teardown at all" possible, because something other
than the agent has to own the window.

- **It receives the DELEGATIONS.** It is told what to place, not how to place it. The
  requesting agent states logical placement only — `none · sibling · child · background`
  (Decision-114) — and never names a window, pane, tab or handle.
- **tmux is the current implementation, NOT the interface.** The surface is defined so
  other window managers can be implemented against it. Plain ssh is the case that proves
  the vocabulary: it can offer no second surface, so `sibling`/`child` must degrade.
- **It synchronises with the SUPERVISOR.** This is what "the supervisor supervises and
  listens" means on this axis.
- **It closes what it opened** (Decision-129), by LISTENING for `lifecycle:stopped` — never
  by being called back and told to clean up. That listening step is the decoupling, and it
  is what survives an agent dying without making the call.

## Findings

- The current close path is call-and-poll, not listen: `agents/groundskeeper.md` step 9
  triggers a window-release primitive and then **polls** for the window's absence for up to
  ~3 minutes, and `agents/landscaper.md:179` still has the landscaper close its own window
  as its last act. Both are what this component replaces.
- `tools/landscaper-teardown.sh` hard-fails on a `@gardener_id` tag that nothing stamps, so
  every close currently stalls at its final step. Sibling task `no-agent-teardown` owns
  deleting that script, `.return-window`, and the tag.

## Questions

- **Does this land with `no-agent-teardown` or after it?** Deleting the teardown without
  this component leaves nothing closing windows at all — the operator is living with that
  stall now, so the gap is not theoretical.
- **What exactly is a "delegation"** on the wire — the specification carries
  `orchard:agent:delegation:begin|end`, but whether placement rides that family or its own
  is unsettled.
- **Plain ssh degradation:** silent, or does the launcher learn it got less than it asked
  for?
- **Does the groundskeeper's worktree-removal gate become event-driven too**, or does it
  keep waiting synchronously on this component's outcome?

## Testing

To agree at scope. Expected shape: an agent requests placement by word, gets a window, and
that window closes on its own when the agent reaches `stopped` — with no agent having
called a teardown and no polling loop anywhere in the path. Observed on the operator's
screen.
