- created: 2026-07-25
- created_by: Sebastien Lambla
- created_during: orchestrator session (operator order, absolute priority)

## Blockers

- None.

## Questions

- None open. Root cause and fix are known; this is a mechanical corrective
  the charter-only delivery never applied.

## Findings

- OPERATOR ORDER (2026-07-25), verbatim intent: the recurring dead-inbox /
  orphaned-folder "big problem" is NOT a real problem — it is a symptom of the
  bus never closing properly, and it has been raised before and still not
  dealt with. Make this ABSOLUTE PRIORITY. The proposed reaper is REJECTED: a
  reaper would only exist to delete the folders that collect and listen
  (the inbox spool + the monitor), and those only orphan because proper close
  does not run. Fix the close, not the litter.
- ROOT CAUSE: session/agent close kills the bus's MONITOR (the `inotifywait`
  watcher) directly, instead of WAKING the bus sidecar with a close/release
  message so it can run its own teardown. Killed externally, the bus never
  gets to: delete its inbox folder, discard remaining content, verify its
  watcher is dead, and depart. So the inbox folder and its accumulated
  messages are left behind — the 244-file `ac9f36c6` orphan and every "dead
  inbox" complaint since.
- ROOT CAUSE SHARPENED (operator, 2026-07-25): this is an instance of a
  broader PREMATURE-KILL pattern — the HOUSEKEEPER (and/or the teardown
  scripts) kills components before those components have had time to clean up
  after themselves. The window/panes are reaped — taking the bus's monitor
  process with them — BEFORE the bus was woken to self-teardown. So the
  ordering is inverted: reaping-the-live happens before the-live-finishes-
  self-cleanup. This directly contradicts Decision-041's own rule ("the
  closing agent kills itself; parents reap only the DEAD"). Suspect sites for
  the fix to re-sequence: `tools/architect-teardown.sh` (window-granular
  `@arch_id` kill, agent-closing D1) and the housekeeper/orchestrator reaping.
  FIX ORDERING — this RESTORES Decision-041 (already ruled), it is not a new
  design. Decision-041: components clean up after THEMSELVES; the closing
  agent kills itself; the orchestrator reaps ONLY an agent that died first.
  So the housekeeper does NOT kill live components at all — that was never
  her job. The rule (operator 2026-07-25):
  (1) each component closes its OWN — the bus, woken via the self-message
      below, closes its monitor and tears its own folder; the architect runs
      its own teardown (release bus → architect-teardown.sh);
  (2) the housekeeper's only destructive touch is FILES (the git close:
      docs, tag, squash-merge, push) and it happens LAST — after components
      have self-closed;
  (3) reaping a component is the ORCHESTRATOR's fallback for one that died
      WITHOUT self-closing — never a routine kill of the live.
  The current bug is exactly the violation: components are being killed
  (by the housekeeper / teardown ordering) BEFORE they self-close, so the
  bus never gets its turn. Restore the decision: self-close first, files
  last, reap only the already-dead.
- PRIOR ART — this was already ruled and only half-delivered:
  - Decision-041 (self-teardown at close; a bus is RELEASED by parent close or
    self-exits when ORPHANED) — charters only, no mechanical enforcement.
  - Decision-046 (active-wake): a bus blocked on its monitor must be WOKEN by
    an inbound message and tear its monitor down ITSELF; killing the monitor
    externally leaves the bus asleep forever. Delivered on f/agent-closing as
    D2 = CHARTER TEXT in agents/bus.md only, explicitly marked
    UNVERIFIED-until-live. The mechanical close path was never changed to
    send the wake, so charter text telling the bus to wake never fires.
  - First live observation (2026-07-21, agent-closing sidecar §Testing)
    already recorded the monitor OUTLIVING the departed bus — evidence the
    charter-only fix did not hold.
- The whole [[bus-message-specifying]] "dead inbox" evidence trail
  (exhibits, the 244-file census, the cost model) traces to THIS bug, not to
  a delivery-model flaw. Closing this removes the symptom the redesign kept
  tripping over. Related: [[bus-singleton]], [[window-closing-owning]],
  [[agent-closing]], [[message-bus]].

## Proposal

Make close mechanically WAKE the bus, and let the bus delete its own folders.

MECHANISM (operator, 2026-07-25) — the wake IS a message, using only today's
mechanics. The bus sidecar is asleep, blocked on its `inotifywait`; the ONLY
thing that wakes it is a message arriving in the folder it watches. So:
- The closing agent SENDS ITSELF a message — "I'm closing, stop all messaging
  function." That write lands in the watched inbox and trips the monitor.
- The bus wakes on it, recognizes the close directive, CLOSES ITS OWN MONITOR
  (the charter already says it knows how — Decision-046), tears down its inbox
  folder, and exits cleanly, leaving NOTHING behind.
- NEVER kill the monitor externally — an externally-killed monitor never gives
  the bus the turn it needs to clean up (the exact current bug).

One corrective, built on that mechanism:
- The close path (architect-teardown, orchestrator retirement) performs the
  self-message wake instead of killing the monitor process.
- On that wake the bus runs its existing teardown: recognize the close signal,
  stop the watcher, VERIFY it is gone, `bus.py teardown` its inbox folder
  (removing the folder that collects) and depart.
- The orphan path (parent already dead, no wake possible) is the one place a
  swept cleanup is legitimate — bounded to that case only, not a general
  reaper.
- No new reaper, no TTL sweeper, no daemon.
Scope to agree at dispatch; the fix touches the teardown scripts and the bus
charter's wake mechanics, not the transport grammar. Same self-message wake is
what assures the cross-agent-notify scenario ([[bus-message-specifying]]
round 18): a live listener is one a message can reach and turn.

## Testing

To agree at dispatch — expected shape: drive a real feature close and observe
(tmux list-panes + bus roster + spool listing) that after `THAT IS ALL` /
`ALL IT IS` no bus inbox folder, monitor process, pane, or session of the
closed feature remains. This is the live-close observation Decision-046 was
left waiting on; it is the gate.
