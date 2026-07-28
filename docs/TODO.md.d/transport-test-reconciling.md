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

## DISCOVERY RESULT 2026-07-29 — the Proposal below is INVALIDATED, and the live bug is a different one

Landscaper discovery on `f/transport-test-reconciling` (7 explorers, read-only, zero
commits) before the session crashed. Flushed here from
`.git/the-works/transport-test-reconciling/20260729-landscaper.md` (uncommittable) so
it survives. **Nothing was built. These findings must be ruled on before any relaunch.**

### THE LIVE BUG IS CROSS-WORKTREE WAKE, AND IT IS CAUSED BY FIX B — verified live

`project_slug()` now returns `<owner>.<repo>@<branch>`, so **every worktree gets its own
orchard directory**. `orchard_send` (`courier.py:1130`) computes `target_project =
ORCHID_PARENT_PROJECT or project_slug()` — it defaults to the SENDER's own directory. A
child in a feature worktree signalling its parent in `main` therefore writes into its own
directory, which the parent never watches. Measured live in that session:
`ORCHID_PARENT_SESSION` set, **`ORCHID_PARENT_PROJECT` UNSET**, sender in
`kaukea.orchids@f-transport-test-reconciling/` while the gardener's courier monitors
`kaukea.orchids@main/`. **A landscaper's own close signal cannot reach its supervisor.**

This is the "agents unable to reach the courier" token waste, and it is CONFIRMED by this
very session: all three supervisors sat all night reporting "no lifecycle signal received"
while their landscapers were alive and working — the signals physically could not arrive.
Fix B solved the mailbox collision and created this; before `@branch`, all worktrees folded
onto one directory so parent/child signalling happened to work.

### The Proposal's revert-first construction is INVALID as written

- **Step 1 would destroy the sidebar rewrite.** It says the transport-reading parts of
  `tools/sidebar.py` return to `1b0ea94`. Commit `9de9975` (2026-07-28) since decomposed
  `sidebar.py` from 3056 → 582 lines across 18 new `sidebar_*.py` modules. The cited
  `sidebar.py:1189` marker read no longer exists at that address.
- **Reverting is not "green at every step" any more.** `tests/test_courier.py` at HEAD
  carries `MonitorCliTests` (5 tests) plus `MakeEnvelopeTests`/`CliRoundTripTests`
  additions. A `courier.py` reverted to `1b0ea94` has no `cmd_monitor`, so those fail
  immediately — reverting STARTS from a worse failure count than the 36 we have now.
- **The five fixes are really four.** `operator_origin` is already fully present at
  `1b0ea94` (envelope param l.538, flag l.556-557, `orchard_send` l.570, CLI l.1566).
  Fix E costs zero work. The predecessor report's "absent before" claims were made
  against `9452ee1` (the close-family-fakes BASE), not against `1b0ea94` — two different
  commits, conflated.
- Of the remaining four: fix B is real (slug), fix D is real and is a two-line
  conditional (`skip_replies`), fix C is real and is **the large one** (~15 functions for
  `monitor`), fix A is the deliberate mailbox retirement.

### Restoration surface is narrower than believed — good news

**Zero commits after `aa848a4` touched `tools/courier.py` or `tools/orchard_topic.py`.**
The revert-and-reapply surface is `courier.py` ALONE; nothing later would be lost by it.
And only ONE non-test consumer of the deleted symbols exists: `orchard_topic.py:106`
(`write_orchard_file` + `orchard_message_name`). Restoring those two functions turns all
10 `test_orchard_topic.py` failures green with **no edit to `orchard_topic.py`**, which is
byte-identical at both commits.

The marker producer/consumer seam at HEAD: reader lives at `sidebar_model.py:545`
(`_iter_feature_markers`), expecting schema-2 `{tasks:[{task|feature, name?, state?,
updated}]}`. **Production writer: none** — only `sidebar_sim.py:606` (a fixture) and test
setup write feature markers; `courier.py:1003` writes only the zero-byte session
heartbeat. At `1b0ea94` the writer was `write_feature_marker` called from
`orchard_deliver`, and its shape matched the reader exactly.

### The `:session:` doubling claim is CORRECT (one explorer got it wrong)

An explorer called it false by tracing a BARE `--to abc123` (prefixed once at l.587,
stripped once at l.906-911). But the failing test is the ALREADY-PREFIXED path:
`cmd_signal` does `to = f":session:{to}"` unconditionally, so `--to :session:abc` becomes
`:session::session:abc`. The de-doubling guard was among the 24 deleted. **The charter
instructs agents to signal `--to :session:<parent>` — already prefixed — so this is the
path actually used in practice.**

### docs/orchard-bus.md staleness — all three claims confirmed, plus more

`l.139` documents `<repo>.<project>`, code is `<owner>.<repo>@<branch>`; storage layout
`l.134-148` omits `<feature>.marker`; `l.180-184` still tags the unfiltered-wake gap
`[GAP, remaining]` which `courier.py:1233-1239` already fixed. Additionally
`operator_origin` is undocumented and task-outcome messages are missing from §2.
`ARCHITECTURE.md` l.175/187 repeat the stale slug, l.124 omits `<feature>.marker`.

### Ground truth at `add50a8`

Full suite: **36 failed, 502 passed, 11 subtests passed, 139s**, 538 tests total. Failing
set matches the recorded list exactly, no drift, safely repeatable.

## OPEN QUESTIONS FOR THE OPERATOR (block relaunch)

1. **Does the cross-worktree wake defect split out as its own expedited task?** It is the
   live token-waste bug, it is small (`ORCHID_PARENT_PROJECT` must be injected at spawn, or
   `orchard_send` must resolve the parent's project rather than defaulting to its own), and
   it is independent of the 24-function restoration. Recommendation: yes — fix it FIRST and
   alone, because every other agent in the fleet is currently unable to signal its parent.
2. **Given revert-first is invalid, does the restoration become patch-forward?** Restore the
   deleted symbols onto HEAD rather than reverting `courier.py` to `1b0ea94` and replaying.
   The narrowed surface (courier.py only, one non-test consumer) makes this materially
   safer than it looked on 2026-07-27. Recommendation: yes, patch-forward.
3. **`tools/sidebar.py` is out of scope entirely now** — confirm, given the rewrite.

## Proposal

**SUPERSEDED IN PART — see DISCOVERY RESULT above. Retained for the ruling it records.**

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
