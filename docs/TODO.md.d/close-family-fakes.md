- created: 2026-07-25
- created_by: Sebastien Lambla
- created_during: orchestrator session (courier board triage)

## Blockers

- ~~⊘[[bus-finishing]]~~ CLEARED (2026-07-26): the bus landed — merged to
  main with the full suite green (332 passed). Round 2 starts now
  (Decision-090 ordering: "the moment bus-finishing lands"). Context kept:
  the operator believes these are FAKE PROBLEMS, symptoms of the old
  fan-out/close design — the round examines them against the finished bus
  instead of building onto the old one.

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
- DELIVERED SUBSTRATE (bus-finishing result, 2026-07-26): flat orchard
  transport under `$XDG_RUNTIME_DIR/orchard/{projects,topics}/`; a CLOSED
  22-subject corpus, exact-match — there is no `finished` subject. A
  landscaper's end reaches its parent as a directed `:session:<parent>`
  `orchard:agent:lifecycle:stopped` (+ `orchard:agent:outcome:success|fail`);
  liveness is the passive `<sessionid>.marker` mtime heartbeat; the courier
  is a per-agent singleton closing by self-message wake. The groundskeeper's
  trigger MUST be phrased in this corpus.
- Bus-finishing deferred two LIVE acceptance checks to post merge+sync+
  restart (sidebar shows activity after the cut; a real close leaves zero
  orphan monitors). The sidebar-witnessing dissolution verdict cites these
  observed-live, not deleted code paths alone.
- Bloom round (2026-07-26, pre-launch, Decision-050): WHAT confirmed current
  against Decision-090; wire vocabulary corrected to the delivered corpus;
  scope boundary vs [[summon-restarting]] and the detected-death trigger
  surfaced as operator questions. Adaptive engine not run (non-interactive
  dispatch) — no convergence number claimed; assessment judgement-based.

## Proposal

RULED (operator, 2026-07-25 afternoon — Decision-090): the build IS the
SUPERVISING CONTROLLER, started immediately when [[bus-finishing]] lands:

- OPERATOR RULING (2026-07-26, gardener session): the flow moves to a
  DEDICATED SUPERVISOR subagent. The gardener only asks it to start the
  work; the supervisor decides which agent runs, detects when work is
  closing or closed (bus lifecycle events), and calls the next agent —
  choreography CENTRALISED, agents blind to one another, the flow decidable
  per task. Constraints preserved: operator gates relayed verbatim, never
  absorbed; creator-owns-and-cleans stays structural one level down (the
  supervisor releases what it creates; the gardener releases the supervisor
  and watches for ITS death); supervision collects, never kills
  (Decision-081); writer writes once — the supervisor choreographs, never
  authors. This amends Decision-090's homing clause ("the gardener's own
  groundskeeper" → the groundskeeper fires inside the gardener's supervisor
  subagent) — formal supersession entry recorded on the implementing branch,
  not before (Decision-006 precedent). Settles the controller-home question:
  the supervisor is built ONCE here; [[summon-restarting]] consumes it.
- The close moves out of the landscaper: the supervisor's groundskeeper
  fires on the landscaper's directed `orchard:agent:lifecycle:stopped`
  (outcome via `orchard:agent:outcome:success|fail`) or on detected death —
  detection mechanism per Question below — and releases what its creator
  scope created — worktree, branch, window — in reverse creation order.
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

## Voluntary deferrals (explicit, not blockers)

- Death-detection HOW (tmux pane-death hook vs process-wait vs operator-
  driven): settled by the [[tmux-topology]] written spec or at this build's
  plan gate — the no-timer ban stands until the operator says otherwise.
- Question-broker sub-agent form, `:session:operator` allowlist bypass,
  focus-reclaim-on-closed: the new tmux/operator-interaction component
  (bus-finishing follow-up 2), not this build.
- `sidebar-registry.json` rename (now courier-allowlist-only, name a
  misnomer) and minor sidebar debts (reject-telemetry old layout,
  `progress_pct`, red RGB): bus-finishing follow-ups 3–4, not this build.

## Testing

Per surviving item at rescope time; the dissolution verdicts themselves are
evidence-based (code paths gone, reproduction impossible).
