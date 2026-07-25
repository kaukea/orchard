- created: 2026-07-25
- created_by: Sebastien Lambla
- created_during: orchestrator session (rollout-sweep rulings)

## Blockers

- THE MESSAGE-BUS WORK (operator clarification, 2026-07-25): summon/window
  automation "is not technically possible until the message bus work is
  done" — the courier arc ([[bus-relay]]; [[fanout-cutover]]) gates this.
  Manual summon is his deliberate interim choice, not a failure state.
- Design-with-operator gate: the naming approach on record is rejected; the
  scheme is designed WITH him when the courier gate opens.

## Questions

- The whole design: how a gardener session is summoned, how windows/sessions
  are named and renamed, and what (if anything) automates it — his scheme,
  from scratch.

## Findings

- OPERATOR RULING (2026-07-25, verbatim substance): window rename NEVER
  worked; the area needs a COMPLETE restart; the sidebar has changed (topic
  transport replaced the old model); broadcasts DO NOT exist any more; and
  `bin/orch` was NEVER approved by him — it was agent-minted spec in the
  gardener skill, now struck from the skill text.
- State of the old assumptions: the fan-out broadcast layer the titling/
  summon machinery leaned on is forbidden (bus-transport-v2 rulings) and its
  cut-over is boarded ([[fanout-cutover]]); `sidebar_v3.py` reads topics, not
  inboxes; last night's fleet rollout renamed the tmux window BY HAND because
  no automation exists.
- Adjacent open tasks this restart supersedes or absorbs pieces of:
  [[orchestrator-identity]] (one gardener per repo, session named after the
  project), [[session-naming]] (done — display forms), [[sidebar-titling]]
  (functional — its pane-title tail was already deferred to "the naming
  rework", which is THIS task).

## Proposal

(unwritten by design — the operator's scheme is the spec; record it here as
it is dictated, then scope the build.)

## Testing

To agree at design time.
