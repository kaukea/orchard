- created: 2026-07-27
- created_by: fable-5
- created_during: f/close-family-fakes

# Messaging restoration: recover the 24 functions the fakes squash reverted, keep its five real fixes

## Blockers

- none — the close-family-fakes merge (dd9586a + fix aa848a4) has landed and pushed.

## Questions

- ~~Was dropping the feature-node marker intended?~~ **CLOSED 2026-07-27 — it was already ruled, twice.** The report recorded this as unruled because it was scoped to the code and to `docs/orchard-bus.md`; the rulings live in the `sidebar-empty-rows` sidecar. **Decision-098** (2026-07-26): agents and subagents are ephemeral, "the task is the one that does not disappear" — once every agent on a task has stopped, the task remains as a single row carrying its terminal state. **Decision-099** (2026-07-26): the orchard marker stops being a zero-byte per-session heartbeat and becomes the durable task node, one file per `(project, feature)`, holding area and task states so a completed task survives without activity; pruning archives it rather than deleting it, so moving the file back rehydrates the feature. The merged code writes only the old zero-byte session heartbeat, which contradicts both. Restoration is required by standing decisions, not a judgement call.
- ~~Fix-forward on `main`, or a feature branch?~~ **Resolved (operator, 2026-07-29): branch**, per this task's own default. Launched as `f/transport-test-reconciling` off current `main` — treated as CRITICAL/expedited given live, ongoing token waste (agents unable to reach the courier), but still through the normal landscaper pipeline, not a direct-to-main patch.

## Findings

- At pre-merge main `1b0ea94`, `tests/test_orchard_transport.py` + `tests/test_orchard_topic.py` = **69 passed, 0 failed** (verified in a detached worktree, 2026-07-27).
- At post-merge main `aa848a4`, the full suite = **429 passed, 36 failed** — all 36 in those two files.
- **CORRECTED 2026-07-27 by the Opus xhigh before/after report** (`.git/the-works/gardener/20260727-messaging-before-after-report.md`; the original premise recorded here was wrong and is struck): the 550 added lines were NOT written against the old git-directory mailbox. That test file contains **zero** references to `courier_root`, `the-works`, or `inbox(`; all twelve added test classes exercise the *orchard* transport, which the merge kept. Deleting them on the old rationale would discard live guarantees.
- **Real cause — an accidental revert, not a design divergence.** The branch base `9452ee1` predates `2fbc3cc` (the `sidebar-empty-rows` squash), which added **24 functions** to `tools/courier.py`. The close-family-fakes squash removed all 24, plus the 5 belonging to the deliberately-retired mailbox. The removed set and the added set match exactly apart from those 5. No test could catch it: the newer work's tests were left in place and simply began to fail.
- **All 36 failures are LOST BEHAVIOUR** — 0 changed-by-design, 0 test drift. `tests/test_orchard_transport.py` is byte-identical before and after; the code moved out from under it. Classes: feature-node marker deleted (15), session-role persistence deleted (5), `init --agent` deleted (1), Decision-091 filename gate deleted (4), `signal --to` de-doubling guard deleted (1), rejection telemetry broken by the deleted writer (10).
- **Live regressions proven by running the code, not reading it:** the sidebar's persistent task rows are dead (`courier.py` no longer writes `<feature-id>.marker`; `sidebar.py:1189` still reads it — with marker the row renders, without it nothing), undoing the operator's 2026-07-26 "the task is the one thing that doesn't disappear" ruling; `signal --to :session:<id>` writes a literal `:session:parentSess.marker`, so the **`finished` signal that triggers the close lands in a mailbox nobody drains**; `orchard_topic.py` rejection telemetry is silently lost behind an existing `except Exception: pass`.
- **The merge's five genuine fixes must be preserved** — each a real, unseen defect at `1b0ea94`, proven live: worktree mailbox collision (a second worktree's `teardown` deleted the first's waiting mail), shared project directory, wake filtering, undeliverable close gate (a relayed `THAT IS ALL` woke nothing), operator-origin flag dropped on orchard sends. Two further CHANGELOG claims — session-end self-wake, monitor reply-consumption — were self-inflicted by this branch and repaired inside it, not pre-existing corrections.
- Open question the report could not settle: **no operator ruling exists on dropping the feature marker.** `docs/orchard-bus.md` omits it, but that document also describes the pre-branch slug shape, so it documents the stale base rather than the merged result.
- Blast radius on the live orchard tree: **operator ruled it not consequential** (2026-07-27) — how many features already lost persisted rows is not worth measuring, and the restoration is not gated on it.
- **Pre-launch bloom verification (2026-07-29):** re-ran `tests/test_orchard_transport.py` + `tests/test_orchard_topic.py` on current `main` (`d3c7a2e`) — still **36 failed, 33 passed**, exact same failure set listed below. `1b0ea94` confirmed still an ancestor of `HEAD` (`git merge-base --is-ancestor` true) — still the correct known-green restoration point. No `f/transport-test-reconciling` worktree/branch exists yet — clear to launch.
- Test-suite blind spot: `tests/test_sidebar.py:122` hand-authors the marker it reads, so no test crosses the producer/consumer seam — which is how 429 tests pass with the feature functionally broken.
- The 36 failing tests:

  - `tests/test_orchard_transport.py::FeatureMarkerTests::test_completed_task_persists_in_the_marker`
  - `tests/test_orchard_transport.py::FeatureMarkerTests::test_delegation_traffic_does_not_change_task_state`
  - `tests/test_orchard_transport.py::FeatureMarkerTests::test_feature_marker_created_with_task_shape`
  - `tests/test_orchard_transport.py::FeatureMarkerTests::test_merge_strips_legacy_shapes_but_keeps_current_task_entries`
  - `tests/test_orchard_transport.py::FeatureMarkerTests::test_no_agent_identity_is_retained_for_display`
  - `tests/test_orchard_transport.py::FeatureMarkerTests::test_outcome_sets_terminal_task_state`
  - `tests/test_orchard_transport.py::FeatureMarkerTests::test_second_delivery_merges_rather_than_truncates`
  - `tests/test_orchard_transport.py::SignalPrefixTests::test_already_prefixed_to_is_not_doubled`
  - `tests/test_orchard_transport.py::OrchardFilenameValidationTests::test_missing_json_extension_is_rejected`
  - `tests/test_orchard_transport.py::OrchardFilenameValidationTests::test_routing_prefix_in_any_component_is_rejected`
  - `tests/test_orchard_transport.py::OrchardFilenameValidationTests::test_valid_shapes_are_accepted`
  - `tests/test_orchard_transport.py::OrchardFilenameValidationTests::test_write_orchard_file_rejects_rather_than_repairs_a_malformed_name`
  - `tests/test_orchard_transport.py::StaticOldSchemaMarkerFailOpenTests::test_old_schema1_marker_is_discarded_not_crashed_on`
  - `tests/test_orchard_transport.py::FailOpenNoIdentityEventTests::test_write_feature_marker_does_not_raise_and_writes_nothing`
  - `tests/test_orchard_transport.py::StaticDelegationEventFeatureMarkerTests::test_real_delegation_event_creates_task_in_working_state_not_terminal`
  - `tests/test_orchard_transport.py::FailOpenMarkerReaderTests::test_malformed_json_feature_marker_loads_empty_not_crashed`
  - `tests/test_orchard_transport.py::FailOpenMarkerReaderTests::test_malformed_json_marker_role_reads_as_absent`
  - `tests/test_orchard_transport.py::FailOpenMarkerReaderTests::test_zero_byte_marker_as_feature_marker_loads_empty_not_crashed`
  - `tests/test_orchard_transport.py::FailOpenMarkerReaderTests::test_zero_byte_marker_role_reads_as_absent`
  - `tests/test_orchard_transport.py::RolePersistenceNeverOverwritesTests::test_absent_role_persist_writes_nothing`
  - `tests/test_orchard_transport.py::RolePersistenceNeverOverwritesTests::test_role_is_never_overwritten_with_nothing`
  - `tests/test_orchard_transport.py::RolePersistenceNeverOverwritesTests::test_role_never_overwrites_an_existing_record`
  - `tests/test_orchard_transport.py::StaticSessionRoleFixtureTests::test_persisting_over_a_real_captured_role_never_overwrites_it`
  - `tests/test_orchard_transport.py::StaticSessionRoleFixtureTests::test_real_captured_role_marker_reads_back_as_landscaper`
  - `tests/test_orchard_transport.py::SessionRoleIdentityFallbackTests::test_declared_role_persists_and_is_recovered_with_no_harness_agent`
  - `tests/test_orchard_transport.py::SessionRoleIdentityFallbackTests::test_static_captured_role_marker_is_recovered_with_no_harness_agent`
  - `tests/test_orchard_topic.py::test_lifecycle_bad_state_is_rejected - as...`
  - `tests/test_orchard_topic.py::test_status_zero_words_is_rejected - Asse...`
  - `tests/test_orchard_topic.py::test_status_three_words_is_rejected - ass...`
  - `tests/test_orchard_topic.py::test_delegation_bad_action_is_rejected - ...`
  - `tests/test_orchard_topic.py::test_outcome_bad_value_is_rejected - asse...`
  - `tests/test_orchard_topic.py::test_task_post_by_non_gardener_is_rejected`
  - `tests/test_orchard_topic.py::test_task_bad_value_is_rejected - assert ...`
  - `tests/test_orchard_topic.py::test_unknown_family_is_rejected - assert ...`
  - `tests/test_orchard_topic.py::test_bare_post_with_no_event_is_rejected`
  - `tests/test_orchard_topic.py::test_telemetry_rejection_filename_ends_in_json`

## Proposal

**OPERATOR RULING 2026-07-27: revert to the functioning bus, then pull in this morning's fixes.**
Construction order is the ruling's substance, not a detail — the base is the known-green
messaging at `1b0ea94`, and the five verified fixes are brought onto it. This is the reverse
of patching 24 functions back into the merged code, and it is safer: the suite is green at
every step instead of climbing back from 36 failures, and each fix lands as an isolated,
individually-testable change.

1. **Restore the working bus** — `tools/courier.py`, `tools/orchard_topic.py` and the
   transport-reading parts of `tools/sidebar.py` return to their `1b0ea94` state, which
   honours Decision-098 and Decision-099. Checkpoint: the two transport test files run
   69 passed / 0 failed, unmodified.
2. **Bring the five verified fixes onto that base**, one commit each, suite green after every one:
   - retire the git-directory mailbox (`courier_root`, `inbox`, `deliver`, `envelope_of`,
     `cmd_list`, the positional-id forms) — this is what fixes the worktree mailbox collision
     where a second worktree's `teardown` deleted the first's waiting mail;
   - per-worktree project directory (`<owner>.<repo>@<branch>`), replacing the slug that
     folded every worktree of a repo onto one path;
   - the `monitor` command: kernel-filtered wake carrying the parsed envelope, with
     `skip_replies` so it cannot eat a blocked caller's reply;
   - deliverable close gate — an unsolicited `:session:` message wakes a standing courier,
     so a relayed `THAT IS ALL` and a `finished` signal actually arrive;
   - `operator_origin` carried on orchard sends, so a relayed operator word is provably his.
3. **Reconcile where restored and new genuinely meet**: the durable task node is keyed under
   the per-worktree slug; the Decision-091 filename gate admits the `:session:` forms while
   still rejecting the malformed literal that today produces `:session:<id>.marker`; the
   session-end hook keeps the full-address form.
4. **Correct `docs/orchard-bus.md`**, which documents the branch's stale base: the slug shape,
   the omitted durable task node (Decision-099), and the "[GAP, remaining]" unfiltered wake
   that `monitor` already fixed.

Keep from the merge, untouched: `agents/supervisor.md`, and the close-dispatch ownership
already ruled at the close.

Out of scope: any new transport capability.

## Testing

- `python3 -m pytest tests -q` on the branch: **0 failed**, with the 36 restored tests passing unmodified — they are the specification, not the thing being fixed.
- Producer/consumer seam covered by a new test that writes through `courier` and reads through `sidebar.build_model` (the seam no existing test crosses, per the report).
- Live check on the real fleet before close: a task row persists after its agent exits, and a `finished` signal addressed `--to :session:<id>` reaches the parent.
