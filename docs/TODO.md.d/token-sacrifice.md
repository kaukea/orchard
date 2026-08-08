- created: 2026-08-08
- created_by: serialseb
- created_during: f/courier-messaging

# Token sacrifice

## Blockers

None.

## Questions

- ~~The SIZE at which the courier recycles~~ RESOLVED 2026-08-08: **25k
  tokens** — "let's be pushy and see how it works." At 25k the courier
  tells its parent to launch a new iteration, then exits.

## Findings

Folded from `bus-recycling.md` (gh#213), 2026-08-08:

- Measured 2026-07-22: a gardener courier grew ~23k → ~53k tokens across 44
  wakes, each late wake replaying the whole transcript to emit one line.
  Rotation is cheap BECAUSE state is on disk: nothing to transfer. (Matches
  the 2026-08-08 measurement: ~19k → ~24.8k over ~15 idle wakes.)
- The harness does not expose token counts to the agent — how the courier
  measures its own depth (wake-count proxy, transcript-size stat, host-side
  counter) is the build's to pick and state.
- The one-per-agent invariant (bus-singleton, Decision-051) holds through
  succession: never two live couriers beyond the crossover instant.
- **Measured 2026-08-08: the launch floor is the HARNESS, not the charter.**
  A do-nothing subagent with a one-line prompt cost 18,285 tokens; the
  courier costs 19,080 — its whole charter is ~800 tokens. System boilerplate,
  tool schemas and injected project files dominate; no charter diet can cut
  the launch cost while the courier is a harness subagent.
- **PROPOSAL (agent, 2026-08-08 — awaiting the operator's word):** implement
  the courier's thinking as a SCRIPT-ISSUED stateless API call to Haiku
  (~600-token prompt: translation table + occasions + validation seed
  examples; ~$0.001/message, ~$0.45/day/agent at 500 msgs/day vs $2.10 for
  the leanest subagent). Nothing accumulates, so the recycle threshold, the
  succession handover and the declared-grace protocol all become moot for
  the thinking layer; only the wake-the-parent hand-up stays harness-side.
  Fits the operator's dumb-courier direction (translation table only, script
  returns the reply) and kills the bypass incentive.
- **Ruled, 2026-08-08 (operator) — the courier runs under its OWN settings
  file:** launch the courier with a dedicated settings file that allowlists
  only the one thing it needs. No unwanted skills in its listing, no project
  instruction files, and a permissions surface so narrow the agent cannot go
  wild — the bypass defense expressed as configuration. The measured 18,285
  floor was under FULL project settings; the true floor under the restricted
  settings file is measured at build time, not estimated.

## Proposal

**Ruled, 2026-08-08 (operator):** the courier is functionally a stateless
translator — the script does the work; it needs a tiny, constant context and
none of the base context — yet its transcript grows with every wake. The
feature: at a MAXIMUM TOKEN COUNT the courier requests its parent to spawn a
new courier; as soon as the new one is spawned, the old one goes away. The
ADDITION over the earlier idea (bus-recycling, gh#213 — same mechanics,
written twice because good ideas come many times over): the old courier must
FINISH its in-flight work — a dispatch, a blocking request/response — before
going, while new messages are denied to it / taken by the new courier.
**Ruled, 2026-08-08 (operator) — the shutdown protocol:** the past race
condition where a courier could not go away because of its monitor must never
repeat. Shutdown is COMMUNICATED, never silent: the departing courier says —
through the status system — that it is shutting down and finishing work, and
declares ONCE a defined amount of time it needs; its owner agent knows of the
shutdown and waits on it for that declared duration. No courier disappears
without information. (Same shape as Decision-060: two closing messages, a
declared grace, then the owner acts.)

Agent advice on the handover mechanics (2026-08-08, awaiting any operator
correction): the inbox belongs to the SESSION, not the courier instance —
succession is monitor ownership changing hands, nothing is forwarded. An
outbox write is atomic and delivery is the dispatch's, so in-flight sends
need no waiting. The only stateful item is an outstanding blocking request:
the old courier keeps a watch narrowed by the script to exactly its awaited
replies, receives nothing else, hands them up, announces stopping/stopped
within its declared grace, and goes.

## Testing

Bound by the parent's testing doctrine (`courier-messaging.md` §Testing, operator ruling 2026-08-08): unit tested to death, including the unit-test seam for an agent communicating with its counterparty; the scenario does not close without its tests written and run green.
