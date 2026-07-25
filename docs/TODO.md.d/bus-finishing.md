- created: 2026-07-25
- created_by: Sebastien Lambla
- created_during: orchestrator session (courier board triage)

## Blockers

- None. The former parity gate on the fan-out cut is DROPPED by operator
  ruling (2026-07-25): "I think it's just killing it" — the old inbox-fed
  sidebar model retires with the fan-out; `sidebar_v3` (topics) is the
  sidebar.

## Questions

- MANUAL AUTH for `:session:` unicast: ruled to exist, shape undefined —
  what does the authorisation step look like in practice? Bring to the plan
  gate; the operator answers in-pane.

## Findings

- THE BUNDLE (operator, 2026-07-25): one feature, one landscaper, closing in
  one go what remains of the bus arc — [[bus-relay]] (+ absorbed
  [[cross-repo-bus]]), [[fanout-cutover]], [[bus-singleton]],
  [[bus-close-cleanup]]. Those four sidecars are the detailed design records;
  this sidecar is the umbrella contract.
- THE GATE this closes (operator): "once request/response lands, the bus is
  good enough." Closing this feature flips [[bus-transport-v2]] to done,
  admits its held changelog entry, unblocks the release cut and
  [[summon-restarting]].
- Request/response: `:session:` unicast, manual auth, DELETED by the script
  upon reading (ruled). Cross-repo reach is the point — target set
  panopticon, seb.throwy, SignMc ("that's the first"); the topic root is
  already user-wide, it is the inbox/unicast leg that is repo-scoped today.
- Fan-out: v1's announce/broadcast fan-out to every inbox is THE money leak
  (~150–200k subagent tokens/day measured); FULL BROADCASTS ARE FORBIDDEN
  (ruled). Kill outright: `depart` is already unread; `test_bus.py`
  broadcast round-trip and `test_bus_traffic` role tests update WITH the
  cut; `sidebar_model.py`'s inbox reads retire with it.
- Singleton + close-cleanup close WITH this build (operator: "should have
  been closed, goes with four, with the analysis we have on what kills
  files and the fixes we already did"): Decision-081 removed all kills —
  agents close themselves; the courier's close must wake it, never kill its
  monitor; exactly one courier per agent.
- Channels ruling (2026-07-25): SendMessage between RELATED agents;
  topics for status/telemetry; UNRELATED-agent messaging is seb.house's,
  out of scope.
- Standing constraints: no log files; no filesystem-as-sync beyond the
  folder-mtime exemption; simplicity — no FIFO or advanced delivery.

## Proposal

One branch finishes the bus:
1. `:session:` request/response — unicast with manual auth, delete-on-read,
   working ACROSS repositories (the addressing substrate; prove on
   panopticon / seb.throwy / SignMc).
2. Fan-out killed outright — announce/broadcast/depart inbox copies gone;
   topics (+ unicast-to-parent where directed) carry everything;
   `sidebar_model.py`'s inbox feed retires; affected tests updated in the
   same change.
3. Courier singleton — exactly one courier sidecar per agent, enforced.
4. Courier close cleanup — the close wakes the courier to release itself;
   no orphan monitors, nothing killed.
After this feature the bus is good enough (operator gate); rounds beyond
(metronome-class transport) are explicitly out.

## Testing

To confirm at the plan gate:
- Assured scenario (carried from bus-message-specifying round 18): an agent
  learns a peer's completion through the courier alone — no git or
  filesystem polling. CROSS-REPO variant: peers in two different
  repositories.
- Post-cut suite green: `test_bus.py` / `test_bus_traffic` updated, all
  courier tests pass; grep proves no fan-out send path remains.
- Singleton proof: a second courier load attempt is refused/absorbed.
- Close proof: a session close leaves zero orphan monitors (ps check) and
  the courier's release is observed.
- LIVE on the operator's screen: the sidebar still shows session activity
  end-to-end after the cut (topics only, no inbox reads).
