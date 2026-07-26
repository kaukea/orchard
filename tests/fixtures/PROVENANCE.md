# Fixture provenance

All files in this directory were CAPTURED FROM THE LIVE SYSTEM on
**2026-07-26** during the `sidebar-empty-rows` feature, and hand-validated
at that time against the operator's own read of the live tree. They are
committed VERBATIM. Do not regenerate, reformat, or "fix" any of them to
match a later code change — a fixture disagreeing with the code is the
signal, not a bug in the fixture (operator ruling, 2026-07-26: round-trip
tests where our own writer produces the input our own reader consumes must
be accompanied by tests over static, hand-validated data, since a writer
and reader can agree on a wrong shape and stay green together — this branch
already hit that once with a rejected marker shape).

- `marker_valid_task.json` — a real `<feature-id>.marker` file as written to
  the live tree by the current (accepted) marker schema: one task, named,
  in the `working` state, no `sessions` block.
- `marker_legacy_rejected_sessions.json` — a real marker captured before the
  schema was corrected: carries a rejected legacy `sessions` block and a
  `tasks[]` entry with only a `label` (no `feature`), alongside one valid
  task entry.
- `event_topic_post_status.json` — a real orchard event envelope as written
  by a topic post (`orchard_topic.py post`): carries `identity`/`status`,
  no `id`/`ts`/`repo`/`project`.
- `event_courier_message_content.json` — a real orchard event envelope as
  written by the courier transport (`courier.py send`): carries
  `id`/`ts`/`repo`/`project`, no `identity`/`status`.
- `pretooluse_sower_transport_post.json` / `pretooluse_courier_transport_post.json`
  — PreToolUse hook payloads for a transport-posting Bash command, carrying
  the literal `agent_type` values captured live from the harness during this
  feature's work: a non-courier agent's Bash call reports `"agent_type":
  "sower"`; a courier subagent's reports `"agent_type": "courier"`. The
  surrounding `tool_input.command`/`hook_event_name`/`tool_name` envelope
  matches the PreToolUse shape `hooks/courier-only-transport.sh` reads
  (`.tool_input.command`, `.agent_type`) and the shape already exercised
  synthetically in `tests/test_courier_only_transport.py`; only the
  `agent_type` values themselves are the literal captured facts these two
  files pin down.

## Transport-half static-data fixtures (step 5a, commits 53629e1/d7a471d)

All six below are genuine bytes copied read-only out of the live
`$XDG_RUNTIME_DIR/orchard` tree — nothing in that tree was ever written,
moved, or deleted to produce any of them.

- `event_gardener_no_identity_live.json` — a real `orchard:agent:delegation:schedule`
  event posted by the root gardener session, carrying NO `identity` block at
  all — the exact "root session posts exactly this" case 53629e1's own commit
  message calls out as the observed failure an isolated lookup used to take
  down. Pins the fail-open contract: this shape must never raise. Captured
  **2026-07-27** (event itself written by the running fleet on 2026-07-26).
- `event_delegation_schedule_live.json` — a real `orchard:agent:delegation:schedule`
  event (landscaper scheduling the `transport-identity` sub-job that became
  this very feature's commit 53629e1), pre-dating the new identity shape
  (no `task`/`task_name`) — a genuine delegation envelope for the delegation
  contract, which did not change shape across these two commits. Captured
  **2026-07-27** (event itself written 2026-07-26).
- `marker_feature_schema1_live.json` — the `sidebar-empty-rows.marker` as it
  stood on the live tree at capture time, **2026-07-27, before the branch
  transport was exercised against it**: schema 1, `tasks[]` keyed by
  `feature` — the OLD shape 53629e1 retires. This file was subsequently
  upgraded in place on the live tree itself (see
  `marker_feature_schema2_live.json` below) — this fixture is now the ONLY
  surviving record of that old shape and CANNOT be recaptured; it is kept
  exactly as originally committed, unmodified by the exercise described
  below.
- `marker_session_heartbeat_empty_live.marker` — a real zero-byte per-session
  heartbeat marker straight off the live tree (mtime-only liveness signal,
  no payload) — pins that a reader touching a marker with no bytes at all
  must not raise. Captured **2026-07-27**. **Paired with
  `marker_session_role_live.marker` below**: the two together pin BOTH
  states of the exact same kind of file — the zero-byte heartbeat before a
  role is persisted to it, and the role-carrying payload after — which is
  precisely the transition d7a471d's resume fix depends on. Do not treat
  either as a duplicate of the other; both are required.
- `event_identity_new_shape_live.json` — a real `orchard:agent:status` event
  (body `"verifying"`, session `e3e3aabd-6578-47e1-898e-df36b3f7c9b7`,
  posted from this worktree's own `tools/orchard_topic.py`): `identity`
  carries `agent`, `feature`, `feature_name`, `task`, `task_name`, `parent`,
  and `name` as a plain alias of `feature_name`. At the time
  `marker_feature_schema1_live.json` above was captured, NOTHING on the live
  tree yet carried this shape (grepped for `task_name` across the whole live
  orchard root: zero hits) — the coordinator then posted one real status
  event through this worktree's own transport, which is what put the new
  shape on the live tree at all. This fixture is that event, copied
  read-only, **captured 2026-07-27**.
- `marker_feature_schema2_live.json` — the SAME `sidebar-empty-rows.marker`
  as `marker_feature_schema1_live.json` above, re-captured **2026-07-27**
  after the event above landed and `merge_feature_marker()` upgraded it IN
  PLACE on the live tree: `schema: 2`, `tasks[]` keyed by `task` (not
  `feature`), each entry carrying its own `name`/`state`/`updated`;
  `area`/`name`/`feature`/`updated` at the marker's top level.
- `marker_session_role_live.marker` — the coordinator's own live per-session
  heartbeat marker, `e3e3aabd-6578-47e1-898e-df36b3f7c9b7.marker` under
  `kaukea.orchids`, re-captured read-only on **2026-07-27** after the
  coordinator ran `courier.py init` from this worktree against their own
  live session: contains `{"role": "landscaper"}`. **This file was a
  zero-byte heartbeat immediately beforehand** — the same file
  `init` had already been touching as a liveness marker — and `init`'s
  role-persistence path (d7a471d) wrote the role INTO that existing
  file rather than creating a new artifact; that in-place upgrade is
  exactly what `marker_session_heartbeat_empty_live.marker` above (the
  before-state of this same kind of file) and this fixture (the
  after-state) together pin. The coordinator also confirmed, on the live
  bus rather than in a fixture, that with `CLAUDE_CODE_AGENT` unset
  `identity_of()` reports `agent_type` "landscaper" resolved from this
  exact file.

No fixture in this set is tool-generated any longer: all seven are bytes
copied read-only off the live tree. Committed verbatim, never regenerated
or reformatted to match a later code change — a fixture disagreeing with
the code is the signal, not a bug in the fixture.
