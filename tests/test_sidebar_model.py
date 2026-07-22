"""Unit tests for tools/sidebar_model.py — the bus reader/aggregator.

Runs under both `python3 -m unittest discover` and `pytest`; stdlib only.
Fixtures are real git-init'd temp repos with bus message files written by
hand (see tests/support.py) — build_model() is exercised end to end, never
mocked.
"""
import os
import sys
import tempfile
import unittest
from pathlib import Path

_TOOLS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools",
)
if _TOOLS_DIR not in sys.path:
    sys.path.insert(0, _TOOLS_DIR)

import sidebar_model  # noqa: E402

from support import (  # noqa: E402
    make_repo, bus_root_of, identity_body, lifecycle_body, envelope, write_message,
)


class _BusFixtureTestCase(unittest.TestCase):
    """One fresh git repo + bus root per test."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.repo = make_repo(self._tmp.name)
        self.bus_root = bus_root_of(self.repo)

    def _put(self, folder, msg_id, sender, body, ts, notify_user=None):
        write_message(
            self.bus_root, folder,
            envelope(msg_id, sender, body=body, ts=ts, notify_user=notify_user),
        )

    def _architect(self, session_id, feature_id, folder=None, name=None):
        """Write the identity announce that makes session_id a renderable
        architect feature."""
        folder = folder or session_id
        self._put(
            folder, f"{session_id}-id", session_id,
            identity_body(session_id, agent_type="architect", feature_id=feature_id,
                          name=name or feature_id.replace("-", " ")),
            ts="2026-01-01T00:00:00.000000+00:00",
        )
        return folder


class StatusMappingTests(_BusFixtureTestCase):
    """The six-state status vocabulary (sidebar-polish item 9, revised —
    working/waiting/idle/awaiting_agent/done/failed), all distinct and
    non-overlapping."""

    def test_lifecycle_states_map_to_expected_status(self):
        expected = {
            "started": "working",
            "building": "working",
            "testing": "working",
            "finished": "done",
            "abandoned": "failed",
        }
        for state, _status in expected.items():
            session_id = f"arch-{state}"
            feature_id = f"feat-{state}"
            self._architect(session_id, feature_id)
            self._put(
                session_id, f"{session_id}-lc", session_id,
                lifecycle_body(state, feature_id=feature_id),
                ts="2026-01-01T00:00:01.000000+00:00",
            )

        fleet = sidebar_model.build_model([self.repo])
        self.assertEqual(len(fleet.repos), 1)
        features = {f.feature_id: f for f in fleet.repos[0].features}

        for state, status in expected.items():
            with self.subTest(state=state):
                feature_id = f"feat-{state}"
                self.assertIn(feature_id, features)
                self.assertEqual(features[feature_id].status, status)

    def test_done_and_failed_never_share_encoding(self):
        # explicit operator correction: done and failed must never share a
        # glyph/status value, however they're derived
        self._architect("arch-done", "feat-done")
        self._put("arch-done", "arch-done-lc", "arch-done",
                  lifecycle_body("finished", feature_id="feat-done"),
                  ts="2026-01-01T00:00:01.000000+00:00")
        self._architect("arch-failed", "feat-failed")
        self._put("arch-failed", "arch-failed-lc", "arch-failed",
                  lifecycle_body("abandoned", feature_id="feat-failed"),
                  ts="2026-01-01T00:00:01.000000+00:00")

        fleet = sidebar_model.build_model([self.repo])
        features = {f.feature_id: f for f in fleet.repos[0].features}
        self.assertEqual(features["feat-done"].status, "done")
        self.assertEqual(features["feat-failed"].status, "failed")
        self.assertNotEqual(features["feat-done"].status, features["feat-failed"].status)

    def test_no_lifecycle_and_no_subagents_is_idle(self):
        self._architect("arch-fresh", "feat-fresh")

        fleet = sidebar_model.build_model([self.repo])
        feature = fleet.repos[0].features[0]
        self.assertEqual(feature.status, "idle")

    def test_active_subagent_marks_working_even_without_lifecycle_push(self):
        self._architect("arch-working", "feat-working")
        self._put("arch-working", "arch-working-s1", "arch-working",
                  "orchid:subagent:start:builder-1",
                  ts="2026-01-01T00:00:01.000000+00:00")

        fleet = sidebar_model.build_model([self.repo])
        feature = fleet.repos[0].features[0]
        self.assertEqual(feature.status, "working")

    def test_pre_terminal_done_lifecycle_is_waiting_on_operator(self):
        # lifecycle "done" (built/tested, awaiting THAT IS ALL) is, by
        # definition, an operator-wait -- not a separate terminal status.
        self._architect("arch-predone", "feat-predone")
        self._put("arch-predone", "arch-predone-lc", "arch-predone",
                  lifecycle_body("done", feature_id="feat-predone"),
                  ts="2026-01-01T00:00:01.000000+00:00")

        fleet = sidebar_model.build_model([self.repo])
        feature = fleet.repos[0].features[0]
        self.assertEqual(feature.status, "waiting")
        self.assertTrue(feature.waiting_on_operator)

    def test_all_six_statuses_are_distinct(self):
        statuses = {"working", "waiting", "idle", "awaiting_agent", "done", "failed"}
        self.assertEqual(len(statuses), 6)


class BlockedOnTests(_BusFixtureTestCase):
    """blocked_on distinguishes "waiting on a component" from "awaiting
    another agent" — the minimal tag added to the blocked lifecycle signal
    since the prior signal shape carried no such distinction."""

    def test_blocked_defaults_to_waiting_on_component(self):
        self._architect("arch-blocked-comp", "feat-blocked-comp")
        self._put("arch-blocked-comp", "arch-blocked-comp-lc", "arch-blocked-comp",
                  lifecycle_body("blocked", feature_id="feat-blocked-comp"),
                  ts="2026-01-01T00:00:01.000000+00:00")

        fleet = sidebar_model.build_model([self.repo])
        feature = fleet.repos[0].features[0]
        self.assertEqual(feature.status, "waiting")
        self.assertFalse(feature.waiting_on_operator)

    def test_blocked_on_agent_is_awaiting_agent(self):
        self._architect("arch-blocked-peer", "feat-blocked-peer")
        self._put("arch-blocked-peer", "arch-blocked-peer-lc", "arch-blocked-peer",
                  lifecycle_body("blocked", feature_id="feat-blocked-peer",
                                blocked_on="agent"),
                  ts="2026-01-01T00:00:01.000000+00:00")

        fleet = sidebar_model.build_model([self.repo])
        feature = fleet.repos[0].features[0]
        self.assertEqual(feature.status, "awaiting_agent")

    def test_blocked_on_component_explicit_is_waiting(self):
        self._architect("arch-blocked-explicit", "feat-blocked-explicit")
        self._put("arch-blocked-explicit", "arch-blocked-explicit-lc", "arch-blocked-explicit",
                  lifecycle_body("blocked", feature_id="feat-blocked-explicit",
                                blocked_on="component"),
                  ts="2026-01-01T00:00:01.000000+00:00")

        fleet = sidebar_model.build_model([self.repo])
        feature = fleet.repos[0].features[0]
        self.assertEqual(feature.status, "waiting")


class WaitingOperatorVariantTests(_BusFixtureTestCase):
    """The ❓ waiting-on-operator variant — driven by last_notify_user (or
    the equivalent lifecycle "done" signal), never by blocked_on=agent."""

    def test_notify_user_flag_marks_waiting_on_operator(self):
        self._architect("arch-notify", "feat-notify")
        self._put("arch-notify", "arch-notify-act", "arch-notify",
                  "orchid:activity:need input",
                  ts="2026-01-01T00:00:01.000000+00:00", notify_user=True)

        fleet = sidebar_model.build_model([self.repo])
        feature = fleet.repos[0].features[0]
        self.assertTrue(feature.waiting_on_operator)
        self.assertEqual(feature.status, "waiting")

    def test_reannounce_after_notify_does_not_clear_waiting(self):
        self._architect("arch-sticky1", "feat-sticky1")
        self._put("arch-sticky1", "arch-sticky1-act", "arch-sticky1",
                  "orchid:activity:need input",
                  ts="2026-01-01T00:00:01.000000+00:00", notify_user=True)
        # a later re-announce (identity push) from the SAME sender, without
        # notify_user, must not clear the still-open waiting flash
        self._put("arch-sticky1", "arch-sticky1-id2", "arch-sticky1",
                  identity_body("arch-sticky1", agent_type="architect",
                                feature_id="feat-sticky1", name="feat sticky1"),
                  ts="2026-01-01T00:00:02.000000+00:00")

        fleet = sidebar_model.build_model([self.repo])
        feature = fleet.repos[0].features[0]
        self.assertTrue(feature.waiting_on_operator)
        self.assertEqual(feature.status, "waiting")

    def test_plain_lifecycle_after_notify_does_not_clear_waiting(self):
        self._architect("arch-sticky2", "feat-sticky2")
        self._put("arch-sticky2", "arch-sticky2-act", "arch-sticky2",
                  "orchid:activity:need input",
                  ts="2026-01-01T00:00:01.000000+00:00", notify_user=True)
        # a later plain lifecycle signal (no notify_user) from the SAME
        # sender must not clear the still-open waiting flash
        self._put("arch-sticky2", "arch-sticky2-lc", "arch-sticky2",
                  lifecycle_body("building", feature_id="feat-sticky2"),
                  ts="2026-01-01T00:00:02.000000+00:00")

        fleet = sidebar_model.build_model([self.repo])
        feature = fleet.repos[0].features[0]
        self.assertTrue(feature.waiting_on_operator)
        self.assertEqual(feature.status, "waiting")

    def test_terminal_lifecycle_clears_waiting(self):
        self._architect("arch-sticky3", "feat-sticky3")
        self._put("arch-sticky3", "arch-sticky3-act", "arch-sticky3",
                  "orchid:activity:need input",
                  ts="2026-01-01T00:00:01.000000+00:00", notify_user=True)
        # a finished session is resolved: the stale waiting flash must clear
        # and the row must show its done status, not the operator glyph
        self._put("arch-sticky3", "arch-sticky3-lc", "arch-sticky3",
                  lifecycle_body("finished", feature_id="feat-sticky3"),
                  ts="2026-01-01T00:00:02.000000+00:00")

        fleet = sidebar_model.build_model([self.repo])
        feature = fleet.repos[0].features[0]
        self.assertFalse(feature.waiting_on_operator)
        self.assertEqual(feature.status, "done")


class AttributionTests(_BusFixtureTestCase):
    def test_activity_attributed_to_sender_not_folder(self):
        self._architect("arch-A", "feat-A")
        # activity FROM arch-A, physically written inside a DIFFERENT
        # session's folder ("arch-B") -- simulates fan_out delivering a copy
        # into a peer's inbox. Attribution must follow envelope['from'],
        # never the folder the file was found in, and no phantom "arch-B"
        # feature must appear (arch-B never announced an identity).
        self._put("arch-B", "arch-A-act", "arch-A", "orchid:activity:working on A",
                  ts="2026-01-01T00:00:01.000000+00:00")

        fleet = sidebar_model.build_model([self.repo])
        self.assertEqual(len(fleet.repos[0].features), 1)
        feature = fleet.repos[0].features[0]
        self.assertEqual(feature.feature_id, "feat-A")
        self.assertEqual(feature.activity, "working on A")


class SubagentTests(_BusFixtureTestCase):
    def test_start_without_done_is_present(self):
        self._architect("arch-sub1", "feat-sub1")
        self._put("arch-sub1", "arch-sub1-s1", "arch-sub1",
                  "orchid:subagent:start:build-agent",
                  ts="2026-01-01T00:00:01.000000+00:00")

        fleet = sidebar_model.build_model([self.repo])
        labels = [s.label for s in fleet.repos[0].features[0].subagents]
        self.assertEqual(labels, ["build-agent"])

    def test_start_then_done_is_absent(self):
        self._architect("arch-sub2", "feat-sub2")
        self._put("arch-sub2", "arch-sub2-s1", "arch-sub2",
                  "orchid:subagent:start:build-agent",
                  ts="2026-01-01T00:00:01.000000+00:00")
        self._put("arch-sub2", "arch-sub2-s2", "arch-sub2",
                  "orchid:subagent:done:build-agent",
                  ts="2026-01-01T00:00:02.000000+00:00")

        fleet = sidebar_model.build_model([self.repo])
        labels = [s.label for s in fleet.repos[0].features[0].subagents]
        self.assertEqual(labels, [])

    def test_self_reported_messaging_label_excluded(self):
        self._architect("arch-sub3", "feat-sub3")
        self._put("arch-sub3", "arch-sub3-s1", "arch-sub3",
                  "orchid:subagent:start:messaging",
                  ts="2026-01-01T00:00:01.000000+00:00")

        fleet = sidebar_model.build_model([self.repo])
        self.assertEqual(fleet.repos[0].features[0].subagents, [])

    def test_bus_sidecar_child_session_excluded(self):
        self._architect("arch-sub4", "feat-sub4")
        # a bus sidecar child session (agent_type "bus") whose parent_session
        # points at the architect must never surface as a subagent row, even
        # though it satisfies the generic parent_session-match rule.
        self._put("bus-child", "bus-child-id", "bus-child",
                  identity_body("bus-child", agent_type="bus", name="messaging",
                                parent_session="arch-sub4"),
                  ts="2026-01-01T00:00:01.000000+00:00")

        fleet = sidebar_model.build_model([self.repo])
        self.assertEqual(fleet.repos[0].features[0].subagents, [])

    def test_two_parents_each_show_their_own_subagents(self):
        # sidebar-polish item 3: EVERY agent's subagents render under their
        # own parent, not just the first feature's.
        self._architect("arch-parentA", "feat-parentA")
        self._put("arch-parentA", "arch-parentA-s1", "arch-parentA",
                  "orchid:subagent:start:builder-A1",
                  ts="2026-01-01T00:00:01.000000+00:00")
        self._put("arch-parentA", "arch-parentA-s2", "arch-parentA",
                  "orchid:subagent:start:builder-A2",
                  ts="2026-01-01T00:00:02.000000+00:00")

        self._architect("arch-parentB", "feat-parentB")
        self._put("arch-parentB", "arch-parentB-s1", "arch-parentB",
                  "orchid:subagent:start:builder-B1",
                  ts="2026-01-01T00:00:01.000000+00:00")
        # arch-parentB also has a peer session (non-bus) parented to it
        self._put("peer-B", "peer-B-id", "peer-B",
                  identity_body("peer-B", agent_type="builder", name="peer-builder-B",
                                parent_session="arch-parentB"),
                  ts="2026-01-01T00:00:01.000000+00:00")

        fleet = sidebar_model.build_model([self.repo])
        features = {f.feature_id: f for f in fleet.repos[0].features}
        self.assertEqual(len(features), 2)

        labels_a = sorted(s.label for s in features["feat-parentA"].subagents)
        labels_b = sorted(s.label for s in features["feat-parentB"].subagents)
        self.assertEqual(labels_a, ["builder-A1", "builder-A2"])
        self.assertEqual(labels_b, ["builder-B1", "peer-builder-B"])


class InternalRowFilteringTests(_BusFixtureTestCase):
    """Rows never operator-facing: a bare session-UUID row (no announced
    name) — sidebar-polish item 2."""

    _UUID = "3fa85f64-5717-4562-b3fc-2c963f66afa6"

    def test_architect_with_no_name_and_no_feature_id_is_hidden(self):
        self._put(self._UUID, f"{self._UUID}-id", self._UUID,
                  identity_body(self._UUID, agent_type="architect"),
                  ts="2026-01-01T00:00:00.000000+00:00")

        fleet = sidebar_model.build_model([self.repo])
        self.assertEqual(fleet.repos[0].features, [])

    def test_subagent_with_no_name_and_uuid_session_id_is_hidden(self):
        self._architect("arch-uuidsub", "feat-uuidsub")
        self._put(self._UUID, f"{self._UUID}-id", self._UUID,
                  identity_body(self._UUID, agent_type="builder",
                                parent_session="arch-uuidsub"),
                  ts="2026-01-01T00:00:01.000000+00:00")

        fleet = sidebar_model.build_model([self.repo])
        self.assertEqual(fleet.repos[0].features[0].subagents, [])

    def test_subagent_with_uuid_session_id_but_announced_name_is_shown(self):
        # a raw-uuid session_id is fine as long as a NAME was announced —
        # only a bare, unnamed uuid row is hidden.
        self._architect("arch-nameduuidsub", "feat-nameduuidsub")
        self._put(self._UUID, f"{self._UUID}-id", self._UUID,
                  identity_body(self._UUID, agent_type="builder", name="named-builder",
                                parent_session="arch-nameduuidsub"),
                  ts="2026-01-01T00:00:01.000000+00:00")

        fleet = sidebar_model.build_model([self.repo])
        labels = [s.label for s in fleet.repos[0].features[0].subagents]
        self.assertEqual(labels, ["named-builder"])


class StaleRowEvictionTests(unittest.TestCase):
    """Root-cause fix: a sender's ENTIRE state is evicted (not just its
    waiting flag) a scan after its terminal lifecycle signal — exercised
    directly against a long-lived _BusAggregator, the only way to observe
    multi-scan behaviour (build_model() always starts a fresh one)."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.repo = make_repo(self._tmp.name)
        self.bus_root = bus_root_of(self.repo)

    def _put(self, folder, msg_id, sender, body, ts):
        write_message(self.bus_root, folder, envelope(msg_id, sender, body=body, ts=ts))

    def test_terminal_state_evicted_one_scan_after_signal(self):
        self._put("arch-stale", "arch-stale-id", "arch-stale",
                  identity_body("arch-stale", agent_type="architect",
                                feature_id="feat-stale"),
                  ts="2026-01-01T00:00:00.000000+00:00")

        agg = sidebar_model._BusAggregator()
        agg.scan(self.bus_root)
        self.assertEqual(agg.repo(self.repo).features[0].status, "idle")

        self._put("arch-stale", "arch-stale-lc", "arch-stale",
                  lifecycle_body("finished", feature_id="feat-stale"),
                  ts="2026-01-01T00:00:01.000000+00:00")
        agg.scan(self.bus_root)
        # same scan the terminal signal arrived on: still visible as "done"
        self.assertEqual(agg.repo(self.repo).features[0].status, "done")

        # neither message file needs to be removed for this: eviction is
        # driven by the terminal signal already observed, not by disk
        # presence (both message ids are already in _seen_ids, so even the
        # still-on-disk identity announce is not re-applied) -- the NEXT
        # scan must evict the sender's state IN FULL, not just its waiting
        # flag, so the row disappears entirely
        agg.scan(self.bus_root)
        self.assertEqual(agg.repo(self.repo).features, [])


class BusRowTests(_BusFixtureTestCase):
    """Bus rows: exactly one collapsed row per live parent agent, never for
    a parent with no bus, never duplicated (sidebar-polish item 5)."""

    def test_no_bus_row_when_no_bus_session(self):
        self._architect("arch-nobus", "feat-nobus")

        fleet = sidebar_model.build_model([self.repo])
        self.assertIsNone(fleet.repos[0].features[0].bus)

    def test_bus_row_present_for_live_architect(self):
        self._architect("arch-hasbus", "feat-hasbus")
        self._put("bus-1", "bus-1-id", "bus-1",
                  identity_body("bus-1", agent_type="bus", name="messaging",
                                parent_session="arch-hasbus"),
                  ts="2026-01-01T00:00:01.000000+00:00")

        fleet = sidebar_model.build_model([self.repo])
        feature = fleet.repos[0].features[0]
        self.assertIsNotNone(feature.bus)
        self.assertEqual(feature.bus.label, sidebar_model.BUS_LABEL)

    def test_duplicate_bus_sessions_collapse_to_one_row(self):
        # a known, separately-root-caused defect (bus-singleton task) can
        # spawn more than one bus session for the same parent -- display
        # must still show exactly one row, never more.
        self._architect("arch-dupbus", "feat-dupbus")
        for i in range(3):
            self._put(f"bus-dup-{i}", f"bus-dup-{i}-id", f"bus-dup-{i}",
                      identity_body(f"bus-dup-{i}", agent_type="bus", name="messaging",
                                    parent_session="arch-dupbus"),
                      ts="2026-01-01T00:00:01.000000+00:00")

        fleet = sidebar_model.build_model([self.repo])
        feature = fleet.repos[0].features[0]
        self.assertIsNotNone(feature.bus)  # exactly one Bus object, not a list

    def test_orchestrator_bus_row(self):
        self._put("orch-1", "orch-1-id", "orch-1",
                  identity_body("orch-1", agent_type="orchestrator"),
                  ts="2026-01-01T00:00:00.000000+00:00")
        self._put("orch-bus", "orch-bus-id", "orch-bus",
                  identity_body("orch-bus", agent_type="bus", name="messaging",
                                parent_session="orch-1"),
                  ts="2026-01-01T00:00:01.000000+00:00")

        fleet = sidebar_model.build_model([self.repo])
        self.assertIsNotNone(fleet.repos[0].bus)


class CrossRepoTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)

    def test_two_repos_both_appear_in_fleet(self):
        repo1 = make_repo(self._tmp.name)
        repo2 = make_repo(self._tmp.name)
        for repo, tag in ((repo1, "one"), (repo2, "two")):
            root = bus_root_of(repo)
            write_message(
                root, f"arch-{tag}",
                envelope(
                    f"arch-{tag}-id", f"arch-{tag}",
                    body=identity_body(f"arch-{tag}", agent_type="architect",
                                       feature_id=f"feat-{tag}"),
                    ts="2026-01-01T00:00:00.000000+00:00",
                ),
            )

        fleet = sidebar_model.build_model([repo1, repo2])
        self.assertEqual(len(fleet.repos), 2)
        self.assertEqual({r.path for r in fleet.repos}, {repo1, repo2})
        feature_ids = {r.features[0].feature_id for r in fleet.repos}
        self.assertEqual(feature_ids, {"feat-one", "feat-two"})


class DedupTests(_BusFixtureTestCase):
    def test_same_id_second_occurrence_across_scans_is_ignored(self):
        # _BusAggregator (not the throwaway one build_model() uses internally)
        # exercised directly across TWO scans -- this is the only way to
        # observe the id-dedup contract described in sidebar_model's own
        # docstring (state persists and re-delivery of an already-seen id is a
        # no-op), since build_model() always starts a fresh aggregator.
        write_message(
            self.bus_root, "arch-dedup",
            envelope("arch-dedup-id", "arch-dedup",
                    body=identity_body("arch-dedup", agent_type="architect",
                                        feature_id="feat-dedup"),
                    ts="2026-01-01T00:00:00.000000+00:00"),
        )
        write_message(
            self.bus_root, "arch-dedup",
            envelope("dup-1", "arch-dedup", body="orchid:activity:first",
                    ts="2026-01-01T00:00:01.000000+00:00"),
        )

        agg = sidebar_model._BusAggregator()
        agg.scan(self.bus_root)
        first_pass = agg.repo(self.repo)
        self.assertEqual(first_pass.features[0].activity, "first")

        # SAME envelope id "dup-1", different body, delivered as a second
        # file (simulates a stale re-delivery) -- must not be re-applied once
        # that id was seen in an earlier scan.
        write_message(
            self.bus_root, "arch-dedup",
            envelope("dup-1", "arch-dedup", body="orchid:activity:second",
                    ts="2026-01-01T00:00:02.000000+00:00"),
            filename="dup-1-retry.json",
        )
        agg.scan(self.bus_root)
        second_pass = agg.repo(self.repo)
        self.assertEqual(second_pass.features[0].activity, "first",
                         "message with an already-seen id must not be re-applied")

    def test_seen_ids_pruned_when_message_removed(self):
        # the underlying message file is ephemeral (deleted by its
        # recipient's receive), so once it's gone from disk its id must be
        # pruned from _seen_ids rather than retained forever.
        write_message(
            self.bus_root, "arch-prune",
            envelope("arch-prune-id", "arch-prune",
                    body=identity_body("arch-prune", agent_type="architect",
                                        feature_id="feat-prune"),
                    ts="2026-01-01T00:00:00.000000+00:00"),
        )

        agg = sidebar_model._BusAggregator()
        agg.scan(self.bus_root)
        self.assertIn("arch-prune-id", agg._seen_ids)

        (Path(self.bus_root) / "arch-prune" / "arch-prune-id.json").unlink()

        agg.scan(self.bus_root)
        self.assertNotIn("arch-prune-id", agg._seen_ids)


class RepoStatusTests(_BusFixtureTestCase):
    def test_repo_without_orchestrator_is_idle(self):
        self._architect("arch-idle", "feat-idle")

        fleet = sidebar_model.build_model([self.repo])
        self.assertEqual(fleet.repos[0].status, "idle")


class FeatureNameTests(_BusFixtureTestCase):
    def test_announced_name_is_used_over_derived_form(self):
        self._architect("arch-namedfeat", "custom-feature", name="Custom Label")

        fleet = sidebar_model.build_model([self.repo])
        feature = fleet.repos[0].features[0]
        self.assertEqual(feature.name, "Custom Label")
        self.assertNotEqual(feature.name, "custom feature")


if __name__ == "__main__":
    unittest.main()
