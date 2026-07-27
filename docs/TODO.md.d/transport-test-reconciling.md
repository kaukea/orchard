- created: 2026-07-27
- created_by: fable-5
- created_during: f/close-family-fakes

# Transport tests: reconcile main's 36 old-model tests with the merged orchard transport

## Blockers

- none — the close-family-fakes merge (dd9586a + fix aa848a4) has landed and pushed.

## Questions

- none open. The per-test port-vs-delete calls are build work, made against the Proposal constraint below.

## Findings

- At pre-merge main `1b0ea94`, `tests/test_orchard_transport.py` + `tests/test_orchard_topic.py` = **69 passed, 0 failed** (verified in a detached worktree, 2026-07-27).
- At post-merge main `aa848a4`, the full suite = **429 passed, 36 failed** — all 36 in those two files.
- Provenance of the failing tests: the close-family-fakes branch (base `9452ee1`) never touched `test_orchard_transport.py`. Main added **550 lines / 33 tests** to it after the branch base, written against the old `the-works` git-directory mailbox transport. The merge kept those tests while the code moved to the orchard project-directory model the operator ruled in at close (2026-07-27) — so they now exercise deleted behaviour.
- These are NOT all disposable: some may encode behavioural rulings (role identity fallback, delivery merge semantics, name validation) the new transport must still honour. Each test needs an explicit port-or-delete call.
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

Make main's test suite green again without reverting the merged transport design.

- For each of the 36 failing tests: either PORT it to the orchard project-directory transport (preserving the behavioural intent it encodes) or REMOVE it as testing behaviour the ruled-in design deleted — with a one-line rationale per removed test recorded in this sidecar.
- Constraint: the operator's close-family-fakes conflict rulings stand — supervisor owns the close, orchard project directory keyed by branch replaces the-works mailboxes, monitor/project-dir command set. No transport code reverts to satisfy a test.
- Out of scope: any new transport capability; any change outside the two test files except where a port reveals a genuine defect in the merged transport (which becomes a Finding + fix in the same branch).

## Testing

- `python3 -m pytest tests -q` on the branch: **0 failed** (429+ passed; count may drop by deliberately removed tests, each with recorded rationale).
- The two transport files run green standalone.
