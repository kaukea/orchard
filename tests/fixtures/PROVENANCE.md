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
