- created: 2026-07-21
- created_by: Sebastien Lambla

## Blockers

- None hard; builds on the merged [[message-bus]].

## Questions

- ~~Is revival universal, or scoped to roles worth reviving?~~ Answered (operator,
  2026-07-21): WHITELISTED child→parent scenarios only — landscaper → gardener for
  now. Subagents are irrelevant by construction (same session id as their parent).
- ~~How does the SessionStart guard distinguish the operator's manual resume from an
  agent's CLI bypass?~~ Resolved (operator, 2026-07-21): it doesn't — no discriminator
  is built. The guard applies uniformly; the operator overrides anything by
  definition, so when blocked they mint the token by hand (one deliberate command).
  A "detect the human" heuristic would be a spoofable ambient hole; an explicit
  override is not.

## Findings

- Operator spec (2026-07-21): delivery to a ZOMBIE (a session that died, e.g. an
  gardener that must be revived) is decided by SCRIPTS, not models — the delivery
  path checks whether the session id still has a live pid; if not, it restores the
  session BEFORE delivering. The respawn race is avoided by a LOCK on the session-id
  folder while respawning.
- Operator refinement (2026-07-21): NOTHING new is recorded at announce. The session id
  alone suffices — `claude --resume <session-id>` restores the session with its own
  context (the harness knows its project/worktree; resume is role-agnostic, so no
  per-role relaunch commands). The pid check is derived at delivery time from the live
  process table, not from announce-time bookkeeping.
- Lock shape ratified in-session: `flock` on the recipient's session-id folder — atomic
  (concurrent deliveries can't both respawn), kernel-held (no lockfile bookkeeping),
  auto-released on holder death (a crashed respawner can't wedge the inbox).
- Honours the no-scheduler ban ([[bus-liveness]]): the check runs only when a message
  needs delivering, never on a timer. Complementary split: [[bus-liveness]] = how death
  is evidenced; THIS task = what delivery does about it.

## Proposal

The courier delivery path gains a script-side liveness gate: under `flock` on the
recipient's session-id folder — is the session id's pid alive? If not, and ONLY if
the revival is authorised, `claude --resume <session-id>`; then unlock and deliver.
Scripts decide everything; models decide nothing. The delivery gate also inherits [[bus-liveness]]'s residue:
when the recipient is dead and revival is not authorised, the SENDER is told so —
dead is distinguishable from chose-not-to-reply.

Authorisation (operator, 2026-07-21 — revival must not be model-decidable, or agents
bypass the gate and burn tokens):

- A message may carry `{resurrect: true}`. The SENDER requests; the delivery SCRIPT
  decides: the flag is honoured only when the (sender role → target role) edge is on
  a whitelist compiled into the script — `{landscaper → gardener}` for now.
  Orphaned agents are the Unix orphan mess replayed in agentic form: nothing adopts
  them automatically. Mail to a dead session without an authorised resurrect just
  queues in the inbox.
- Direct-CLI bypass dies at birth: when the script legitimately revives, it writes a
  ONE-SHOT resurrection token (nonce + edge + timestamp) into the dead session's courier
  folder before `claude --resume`, consumed at start. The SessionStart hook — which
  already runs everywhere — adds one stat(): session registered dead + no valid token
  → refuse the boot before any model turn runs. A model resuming by hand gets a
  session that dies pre-inference, at zero token cost.
- Performance: one tuple lookup in an already-running delivery + one stat() in an
  already-firing hook. No permission classifier, no CLI wrapping, no scheduler.

## Testing

To agree when bloomed — expected shape: kill a session, send it a message → the script
revives it (correct worktree, correct role, via resume) and the message arrives; N
concurrent sends to the same zombie produce exactly ONE respawn and N delivered
messages.
