- created: 2026-08-08
- created_by: serialseb
- created_during: f/courier-messaging

# Pub/sub, including NAME addressing

## Blockers

None.

## Questions

None open.

## Findings

- The archived branch implements the layer main lacks: `subscribe` creates
  `orchard/topics/<name>/<sid>/`, publish fans copies into currently
  subscribed folders only, monitor adds only subscribed folders as watch
  sources (`93f44f5` and surroundings). The 2026-08-08 courier self-wake on
  main is the absence of this layer.
- The branch's NAME-addressing code (script-minted registry, nearest-first
  resolution, fan-out to every live holder) is AGENT-name machinery — reference
  material for `tree-messaging.md`, not for this task.

## Proposal

Pub/sub as dictated 2026-08-08. **Clarified by the operator, 2026-08-08: the
NAME here is the TOPIC name** — agent-name addressing is a different name
entirely and lives in `tree-messaging.md`; the two have nothing to do with
one another.

**Extracted from existing rulings, 2026-08-08 (sources named — not re-asked):**

- **Who creates/closes topics:** team topics for a feature or task are set up by
  the SUPERVISOR, which owns which topics exist and who is on them
  (Decision-133). The PROJECT topic is bound to the project's life — created at
  project open, closed at project close (operator ruling 2026-08-08,
  `project-broadcast.md`); a project is the git repo, one topic per repo shared
  by all its worktrees (Decision-084).
- **Membership:** team-topic membership is the supervisor's (Decision-133);
  an observer/consumer subscribes itself to watch (publish-and-monitor,
  Decision-130).
- **What rides a topic:** raw states only, from the closed 22-subject corpus,
  exact membership, variable data in the body never the subject (Decisions
  082/092) — matching the operator's 2026-08-08 subject/address orthogonality
  ruling. Identity and status are supplied by the SCRIPT, never authored by
  agents (Decision-082).
- **Ruled, 2026-08-08 (operator):** messages are SELF-DESCRIPTIVE, which is
  what lets one outbox serve everything: the sender drops the message in its
  outbox and it goes to the right place. For pub/sub that place is the TOPIC,
  where the message STAYS while a crawler component copies it into the inbox
  of every component subscribed to the topic. The message is cleared from the
  topic once ALL CURRENT subscribers have received it — so nobody can receive
  messages from before their subscription; no replay. The topic itself is
  cleared once it holds no messages and has seen no activity for an amount of
  time — a garbage collector, like everyone else ends up with. This supersedes
  the branch's per-topic per-subscriber folders.

## Testing

Bound by the parent's testing doctrine (`courier-messaging.md` §Testing, operator ruling 2026-08-08): unit tested to death, including the unit-test seam for an agent communicating with its counterparty; the scenario does not close without its tests written and run green.
