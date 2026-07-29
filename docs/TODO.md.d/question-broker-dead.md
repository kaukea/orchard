- created: 2026-07-29
- created_by: gardener
- created_during: main

# The question broker is built, tested and NOT RUNNING — every agent's `ask` path is dead

## Questions

1. **Does `courier.py ask` survive as a distinct command, or does asking the operator
   become `courier.py send --to :session:operator ...` followed by an ordinary blocking
   wait for a reply, with the broker as just another consumer of `:session:operator`
   mail?**
   GROOMER'S READING — not ruled: the ruling's own wording ("traditional
   request/response, no special-casing") reads as "collapse `ask` into `send`+`wait`,
   with the option-list/title/summary shape becoming ordinary BODY content the broker
   interprets — not a distinguished wire subject." But the ruling does not say whether
   the CLI verb `ask` itself is removed, kept as a thin convenience wrapper over
   `send`+`wait`, or kept and only its internals change. This changes the size of the
   task materially (touch one function vs. touch the CLI surface every charter already
   names as "your courier's `ask`"). Recommendation: keep the verb `ask` as a thin
   client-side convenience (so charters don't need a rewrite) but implement it as an
   ordinary directed request under the hood, with no bespoke envelope construction and
   no bespoke wait loop — reusing whatever `send`+`wait for reply` primitive ordinary
   agent-to-agent requests use once `bus-addressing` lands. Needs operator confirmation
   because it is a design choice, not a fact.

2. **Where does the broker mount from, concretely — and is deciding that THIS task's
   job, or does it belong to a sibling?** The sidecar already listed this as an open
   design question before this round ("session hook, sidebar mount, systemd user unit").
   Decision-114 places the UI-placement component (which pops the popup) with the
   plugin subagent that owns placement — that's `sidebar-teamwork`/`no-agent-teardown`
   territory per the parent sidecar's task list, not this one. But WHO STARTS the
   broker process is a deployment question, not a placement question, and nothing in
   Decision-114 assigns it. GROOMER'S READING — not ruled: keep deployment (a mount
   hook, likely alongside `sidebar-mount.sh`'s pattern) in THIS task's scope, since it's
   the direct fix for "not running," and leave popup/UI mechanics to the placement
   component this task already treats as out of scope. Needs operator confirmation.

3. **What does an agent do when it asks and no one is draining the operator mailbox —
   i.e., what does "fail loudly" return, and to whom?** Decision-124's mechanical-not-prose
   shape demands the call itself detect the missing consumer rather than hang, but the
   sidecar doesn't yet specify the mechanism. Candidates: (a) a liveness marker file the
   broker touches periodically (mirroring the `<sessionid>.marker` heartbeat pattern
   `docs/orchard-bus.md` §3 already uses for session liveness) that `ask` checks before
   blocking and refuses immediately if stale/absent; (b) a bounded timeout on the wait
   with a distinct error message. GROOMER'S READING — not ruled: (a) fits the existing
   heartbeat idiom better than inventing a timeout number nobody can justify, and keeps
   "loud failure" instantaneous rather than "loud after N minutes." Needs operator
   confirmation — this is the crux of the Decision-124 mechanical-enforcement
   requirement and shouldn't be inferred silently.

4. **Does the now-stale `#gardener` charter line (gardener claims it posts status via
   `orchard_topic.py` directly, but the tool now refuses any caller but a courier) get
   fixed in this task or filed separately?** Already flagged in Findings below as
   "worth settling in the same round" but not yet a ruling. GROOMER'S READING — not
   ruled: separate task — it's an agent→transport surface bug unrelated to the
   ask/operator path this task is scoped to, and folding it in risks the same
   partial-landing problem the parent sidecar's "why one feature not six" section warns
   against for a DIFFERENT boundary. Recommend a follow-up task, not a scope add here.

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
- **Confirmed by reading every hook and mount script in the tree, not by git history:**
  nothing invokes `tools/orchard-question-broker-mount.sh`. `hooks/courier-init.sh` (the
  SessionStart hook) calls `courier.py init` and prompts the model to spawn a courier
  subagent — it never calls the broker mount. `hooks/question-input-activity.sh` and
  `hooks/question-notification-backstop.sh` both reference the broker in comments but
  neither one mounts it; they assume it is already running. There is no `sidebar-mount.sh`
  equivalent for the broker anywhere in `hooks/` or `.claude/`. This corroborates the
  sidecar's opening claim exactly: mounted from nowhere.
- `cmd_ask` (`tools/courier.py:677`) sends via a hand-built envelope and calls
  `_await_orchard_reply_forever()` (`tools/courier.py:664`), which loops
  `_match_answer()` on a plain `while True` with no deadline and no check that anything
  is draining `:session:operator`. This is the mechanism of the silent hang, and it is
  also the exact shape the operator's ruling says must not exist as a special case.

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
   mounted from nowhere. See Question 2.
2. **Failure is visible** — `ask` refuses, loudly and immediately, when no broker is
   draining. An undeliverable question must return an error to the caller, never a
   silent wait. This is the Decision-124 shape: enforce mechanically, because the prose
   rule "always use `ask`" is already being followed and is already producing the stall.
   See Question 3.

**RESHAPED by operator ruling, 2026-07-29 (recorded verbatim in
`docs/TODO.md.d/observability.md` §"Asking the OPERATOR is a request like any other").**
The scope above is now incomplete in one respect: it treated the fix as "deploy the
existing machinery, don't touch the design." The operator has since ruled the design
itself changes:

> Asking the operator a question is MISSING from the specification and must be encoded
> exactly the same way as any other request/response. The tmux ask component picks up
> the request, displays it, and returns the response to the agent. Traditional
> request/response. The operator is a recipient like any other — there is no special
> question class, no special sender, no bespoke path.

That is a redesign of `courier.py cmd_ask` (`tools/courier.py:677`), which today IS a
special sender class: it builds its own envelope inline (hardcoded
`to=":session:operator"`, `subject="orchard:agent:message:request"`), calls
`orchard_send()` directly rather than going through the ordinary `send`/`reply` verbs,
and blocks forever in `_await_orchard_reply_forever()` with no liveness check on the
broker at all (confirmed by reading the function, 2026-07-29). Under the ruling, asking
the operator should be indistinguishable at the transport layer from any other directed
request — the operator's session id is just another `:session:` address, and the
"special" part collapses to policy (which options, which UI) that already lives in
`orchard-question-broker.py`, not in a bespoke sender. See Question 1 for how far the
redesign reaches into the CLI surface.

Also ruled in the same round, directly bearing on this task: **waiting on an answer is a
NORMAL part of the lifecycle** (the agent is `started`, not `stopping`) — so nothing in
this task's fix should mark a waiting asker as blocked/stopped in the lifecycle sense;
`blocked`/`waiting` are STATUS only, for a UX. The mechanical loud-failure requirement
(Decision-124 shape, above) is about the CALL failing when undeliverable, not about the
wait itself being illegitimate.

**Out of scope, confirmed still true under the reshape:** where questions are visually
presented (popup vs. other UI) stays with the placement component per Decision-114 — see
Question 2 for the deployment/placement boundary this task sits next to.

## Testing

To agree at scope. Expected shape: from a cold session, an agent calls `ask` (or its
post-redesign equivalent), the operator sees a dialog, answers it, and the agent
receives the answer and proceeds — proven end to end by the agent acting on the reply.
Then, with the broker deliberately stopped, the same call returns a visible error
rather than hanging. Token cost of the redesigned call path is worth a before/after
note per the parent sidecar's testing standard, though this task's contribution is a
single message shape rather than the fleet-wide measurement owned by `observability`.
