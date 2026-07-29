- created: 2026-07-29
- created_by: gardener
- created_during: main

# The question broker is built, tested and NOT RUNNING — every agent's `ask` path is dead

## Proposal

Every agent charter in the fleet routes operator questions through the courier's `ask`
("questions to the operator go through your courier's `ask` only — never a native UI
popup"). That path terminates at a standalone question broker which drains the reserved
`:session:operator` mailbox, pops the dialog, and writes the reply back.

**The broker is not running.** Confirmed live 2026-07-29: no broker process on the box.
It is not missing — `tools/orchard-question-broker.py` exists, with a mount script
(`tools/orchard-question-broker-mount.sh`) and 60 tests in
`tests/test_orchard_question_broker.py`. Built, tested, never deployed.

The consequence is worse than a dead feature: it is a **silently** dead feature. An agent
following its charter sends the ask, gets no error, and waits. The operator never sees a
question and the agent stalls at a gate forever. Agents that notice fall back to the
native popup — a charter deviation forced by a broken channel, logged as exactly that by
the `close-family-fakes` landscaper on 2026-07-27.

Scope: make the broker actually run, and make its absence loud rather than silent. Two
parts, both required:

1. **Deployment** — the broker starts and stays up. Where it is mounted from (session
   hook, sidebar mount, systemd user unit) is the design question; it is currently
   mounted from nowhere.
2. **Failure is visible** — `ask` refuses, loudly and immediately, when no broker is
   draining. An undeliverable question must return an error to the caller, never a
   silent wait. This is the Decision-124 shape: enforce mechanically, because the prose
   rule "always use `ask`" is already being followed and is already producing the stall.

**Out of scope:** redesigning where questions are presented. Decision-114 places
`notify_user` and `ask` with the plugin subagent that owns UI placement, which is a
larger reorganisation; this task makes the existing, built machinery work.

## Findings

- Charter-following agents are the ones that stall. An agent that ignores the rule and
  pops a native dialog gets an answer. That inverts the incentive the rule exists to
  create, and it is why this is filed `critical`.
- The one recorded deviation is well-reasoned and should be read before designing the
  fix: the landscaper argued the charter's own PURPOSE (questions must NOTIFY, not stall
  silently) pointed at the popup once the courier reported the ask undeliverable. It
  tried `ask` twice first. The rule and its purpose disagreed because the channel was
  down.
- Related but distinct: the `#gardener` charter states the gardener posts status by
  calling `orchard_topic.py` directly, while the tool itself now refuses any caller but
  a courier ("Only the courier subagent may post on the transport"). Observed 2026-07-29.
  Charter and mechanism disagree; the mechanism wins, so the charter line is stale. Worth
  settling in the same round as the ask path, since both are agent→operator/transport
  surfaces where the written rule no longer matches the code.

## Testing

To agree at scope. Expected shape: from a cold session, an agent calls `ask`, the
operator sees a dialog, answers it, and the agent receives the answer and proceeds —
proven end to end by the agent acting on the reply. Then, with the broker deliberately
stopped, the same call returns a visible error rather than hanging.
