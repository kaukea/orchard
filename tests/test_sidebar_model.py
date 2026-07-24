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
from unittest import mock

_TOOLS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools",
)
if _TOOLS_DIR not in sys.path:
    sys.path.insert(0, _TOOLS_DIR)

import sidebar_model  # noqa: E402
import orchard_registry  # noqa: E402

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

    def _put_ask(self, folder, msg_id, sender, question_id, subject, ts, notify_user=True):
        """A WIRE GRAMMAR v1 ask envelope — question_id/in_reply_to are
        sibling envelope fields, not part of `body`, so they are layered onto
        the base envelope() shape here rather than in support.py (out of
        this step's edit scope)."""
        env = envelope(msg_id, sender, body=f"orchid:interrupt:question:{subject}",
                       ts=ts, notify_user=notify_user)
        env["question_id"] = question_id
        write_message(self.bus_root, folder, env)

    def _put_reply(self, folder, msg_id, sender, in_reply_to, ts, body="ack"):
        env = envelope(msg_id, sender, body=body, ts=ts)
        env["in_reply_to"] = in_reply_to
        write_message(self.bus_root, folder, env)

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
    """Root-cause fix: a sender's ENTIRE state used to be evicted a scan
    after its terminal lifecycle signal, for BOTH finished and abandoned —
    exercised directly against a long-lived _BusAggregator, the only way to
    observe multi-scan behaviour (build_model() always starts a fresh one).

    Operator decision, 2026-07-24 (sidebar-titling item 7): a done feature's
    row must never leave the current sidebar's view. `finished` senders are
    now retained forever (never evicted); `abandoned` senders keep the prior
    one-scan-grace-then-evict behaviour."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.repo = make_repo(self._tmp.name)
        self.bus_root = bus_root_of(self.repo)

    def _put(self, folder, msg_id, sender, body, ts):
        write_message(self.bus_root, folder, envelope(msg_id, sender, body=body, ts=ts))

    def test_finished_state_is_retained_across_many_scans(self):
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
        # same scan the terminal signal arrived on: visible as "done"
        self.assertEqual(agg.repo(self.repo).features[0].status, "done")

        # a done feature's row never leaves — it must still be present (and
        # still "done") across many further scans, not evicted after one
        # scan's grace, and not requiring the message files to still exist
        # on disk (both ids are already in _seen_ids so re-applying is moot).
        for _ in range(5):
            agg.scan(self.bus_root)
            self.assertEqual(agg.repo(self.repo).features[0].status, "done")

    def test_abandoned_state_evicted_one_scan_after_signal(self):
        self._put("arch-fail", "arch-fail-id", "arch-fail",
                  identity_body("arch-fail", agent_type="architect",
                                feature_id="feat-fail"),
                  ts="2026-01-01T00:00:00.000000+00:00")

        agg = sidebar_model._BusAggregator()
        agg.scan(self.bus_root)
        self.assertEqual(agg.repo(self.repo).features[0].status, "idle")

        self._put("arch-fail", "arch-fail-lc", "arch-fail",
                  lifecycle_body("abandoned", feature_id="feat-fail"),
                  ts="2026-01-01T00:00:01.000000+00:00")
        agg.scan(self.bus_root)
        # same scan the terminal signal arrived on: still visible as "failed"
        self.assertEqual(agg.repo(self.repo).features[0].status, "failed")

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


class HasSessionTests(_BusFixtureTestCase):
    """has_session (item 3, "empty projects don't render"): True only when
    the repo has a live orchestrator session or at least one feature; False
    for a repo whose bus is empty (nothing renderable), which the renderer's
    flatten() then skips."""

    def test_no_orchestrator_and_no_features_is_false(self):
        fleet = sidebar_model.build_model([self.repo])
        self.assertEqual(len(fleet.repos), 1)
        self.assertFalse(fleet.repos[0].has_session)

    def test_orchestrator_session_alone_is_true(self):
        self._put("orch-only", "orch-only-id", "orch-only",
                  identity_body("orch-only", agent_type="orchestrator"),
                  ts="2026-01-01T00:00:00.000000+00:00")

        fleet = sidebar_model.build_model([self.repo])
        self.assertTrue(fleet.repos[0].has_session)

    def test_feature_alone_is_true(self):
        self._architect("arch-hassession", "feat-hassession")

        fleet = sidebar_model.build_model([self.repo])
        self.assertTrue(fleet.repos[0].has_session)


class FeatureNameTests(_BusFixtureTestCase):
    def test_announced_name_is_used_over_derived_form(self):
        self._architect("arch-namedfeat", "custom-feature", name="Custom Label")

        fleet = sidebar_model.build_model([self.repo])
        feature = fleet.repos[0].features[0]
        self.assertEqual(feature.name, "Custom Label")
        self.assertNotEqual(feature.name, "custom feature")


class ResolveReposRegistryTests(unittest.TestCase):
    """resolve_repos()'s new primary discovery (sidebar-polish item 7a):
    orchard-registry-driven, current repo self-registers via .ai.toml, hidden
    repos excluded (item 7b). Every test isolates its own registry file so
    the real ~/.config/orchids/sidebar-registry.json is never touched."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.registry_path = Path(self._tmp.name) / "sidebar-registry.json"
        self._patch = mock.patch.object(orchard_registry, "REGISTRY_PATH", self.registry_path)
        self._patch.start()
        self.addCleanup(self._patch.stop)
        # ORCHIDS_SIDEBAR_REPOS must not leak in from the real environment
        # and steer resolve_repos() away from the registry path under test.
        self._env_patch = mock.patch.dict(os.environ, {"ORCHIDS_SIDEBAR_REPOS": ""})
        self._env_patch.start()
        self.addCleanup(self._env_patch.stop)

    def _repo_with_ai_toml(self, name: str) -> str:
        repo_dir = Path(self._tmp.name) / name
        repo_dir.mkdir(parents=True, exist_ok=True)
        (repo_dir / ".ai.toml").write_text("# managed by kauk\n", encoding="utf-8")
        return str(repo_dir)

    def test_current_repo_self_registers_and_is_returned(self):
        repo = self._repo_with_ai_toml("self-registering")
        with mock.patch.object(sidebar_model, "_current_repo", return_value=repo):
            resolved = sidebar_model.resolve_repos()
        self.assertEqual(resolved, [repo])
        self.assertIn(repo, orchard_registry.registered_repos())

    def test_previously_registered_repo_appears_without_being_current(self):
        other = self._repo_with_ai_toml("other-repo")
        orchard_registry.register_repo(other)
        with mock.patch.object(sidebar_model, "_current_repo", return_value=None):
            resolved = sidebar_model.resolve_repos()
        self.assertEqual(resolved, [other])

    def test_hidden_repo_excluded_from_resolution(self):
        visible = self._repo_with_ai_toml("visible-repo")
        hidden = self._repo_with_ai_toml("hidden-repo")
        orchard_registry.register_repo(visible)
        orchard_registry.register_repo(hidden)
        orchard_registry.hide_repo(hidden)

        with mock.patch.object(sidebar_model, "_current_repo", return_value=None):
            resolved = sidebar_model.resolve_repos()

        self.assertEqual(resolved, [visible])
        self.assertNotIn(hidden, resolved)

    def test_hiding_the_only_registered_repo_resolves_empty_not_forced_fallback(self):
        # a registry with entries, all hidden, must resolve to [] -- hiding
        # the sidebar's only repo must actually hide it, never fall back to
        # showing the current repo anyway as if the registry were empty.
        only = self._repo_with_ai_toml("only-repo")
        orchard_registry.register_repo(only)
        orchard_registry.hide_repo(only)

        with mock.patch.object(sidebar_model, "_current_repo", return_value=only):
            resolved = sidebar_model.resolve_repos()

        self.assertEqual(resolved, [])

    def test_empty_registry_and_no_current_repo_resolves_empty(self):
        with mock.patch.object(sidebar_model, "_current_repo", return_value=None):
            resolved = sidebar_model.resolve_repos()
        self.assertEqual(resolved, [])

    def test_explicit_repolist_argument_bypasses_registry_entirely(self):
        # the pre-existing explicit-argument contract (used by every other
        # test in this module) must still short-circuit before any registry
        # or current-repo lookup happens.
        with mock.patch.object(sidebar_model, "_current_repo", return_value="/should-not-be-used"):
            resolved = sidebar_model.resolve_repos(["/explicit/repo"])
        self.assertEqual(resolved, ["/explicit/repo"])


class ResolveReposEnvOverrideTests(unittest.TestCase):
    """ORCHIDS_SIDEBAR_REPOS survives as an explicit, optional override
    (architect HOW decision) — when set, it is read verbatim and the
    registry/current-repo path is never consulted."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        # point REGISTRY_PATH somewhere private too, so if the override
        # accidentally fell through to the registry this test would fail
        # loudly rather than touching the real file.
        self._registry_patch = mock.patch.object(
            orchard_registry, "REGISTRY_PATH", Path(self._tmp.name) / "unused-registry.json",
        )
        self._registry_patch.start()
        self.addCleanup(self._registry_patch.stop)

    def test_env_var_repolist_file_read_verbatim(self):
        repolist_file = Path(self._tmp.name) / "manual-repolist"
        repolist_file.write_text("/manual/repo-a\n# a comment\n\n/manual/repo-b\n",
                                  encoding="utf-8")

        with mock.patch.dict(os.environ, {"ORCHIDS_SIDEBAR_REPOS": str(repolist_file)}):
            with mock.patch.object(sidebar_model, "_current_repo",
                                    return_value="/should-not-be-used"):
                resolved = sidebar_model.resolve_repos()

        self.assertEqual(resolved, ["/manual/repo-a", "/manual/repo-b"])

    def test_env_var_set_but_file_missing_resolves_empty(self):
        missing = Path(self._tmp.name) / "does-not-exist"
        with mock.patch.dict(os.environ, {"ORCHIDS_SIDEBAR_REPOS": str(missing)}):
            resolved = sidebar_model.resolve_repos()
        self.assertEqual(resolved, [])


# --------------------------------------------------------------------------
# WIRE GRAMMAR v1 (bus-message-specifying B3)
# --------------------------------------------------------------------------

class StatusWordTests(_BusFixtureTestCase):
    def test_status_prefix_sets_status_word_and_mirrors_activity(self):
        self._architect("arch-sw1", "feat-sw1")
        self._put("arch-sw1", "arch-sw1-sw", "arch-sw1", "orchid:status:building",
                  ts="2026-01-01T00:00:01.000000+00:00")

        fleet = sidebar_model.build_model([self.repo])
        feature = fleet.repos[0].features[0]
        self.assertEqual(feature.status_word, "building")
        # feature.activity is the pre-existing renderer-facing field (sidebar.py
        # reads it directly) — it must keep mirroring the live doing-word so
        # the renderer needs no change in this step.
        self.assertEqual(feature.activity, "building")

    def test_deprecated_orchid_activity_prefix_still_falls_back_to_status_word(self):
        # one-transition-release fallback: a sender still on the old grammar
        # must not go blank in the sidebar.
        self._architect("arch-sw2", "feat-sw2")
        self._put("arch-sw2", "arch-sw2-legacy", "arch-sw2",
                  "orchid:activity:doing legacy work",
                  ts="2026-01-01T00:00:01.000000+00:00")

        fleet = sidebar_model.build_model([self.repo])
        feature = fleet.repos[0].features[0]
        self.assertEqual(feature.status_word, "doing legacy work")
        self.assertEqual(feature.activity, "doing legacy work")


class UpdateTextTests(_BusFixtureTestCase):
    def test_update_sets_update_text(self):
        self._architect("arch-upd1", "feat-upd1")
        self._put("arch-upd1", "arch-upd1-u", "arch-upd1",
                  "orchid:update:shipped the migration",
                  ts="2026-01-01T00:00:01.000000+00:00")

        fleet = sidebar_model.build_model([self.repo])
        feature = fleet.repos[0].features[0]
        self.assertEqual(feature.update_text, "shipped the migration")

    def test_update_never_drives_status_derivation(self):
        self._architect("arch-upd2", "feat-upd2")
        self._put("arch-upd2", "arch-upd2-u", "arch-upd2",
                  "orchid:update:a long narrative sentence",
                  ts="2026-01-01T00:00:01.000000+00:00")

        fleet = sidebar_model.build_model([self.repo])
        feature = fleet.repos[0].features[0]
        self.assertEqual(feature.status, "idle")

    def test_update_never_sets_notify_even_if_flagged(self):
        # defensive: the grammar says update never notifies, but the
        # aggregator must not trust an envelope that claims otherwise.
        self._architect("arch-upd3", "feat-upd3")
        self._put("arch-upd3", "arch-upd3-u", "arch-upd3",
                  "orchid:update:need review", ts="2026-01-01T00:00:01.000000+00:00",
                  notify_user=True)

        fleet = sidebar_model.build_model([self.repo])
        feature = fleet.repos[0].features[0]
        self.assertFalse(feature.waiting_on_operator)
        self.assertEqual(feature.status, "idle")


class PhaseProgressTests(_BusFixtureTestCase):
    def test_phase_without_tick_uses_base_pct(self):
        self._architect("arch-ph1", "feat-ph1")
        self._put("arch-ph1", "arch-ph1-p", "arch-ph1", "orchid:phase:designing",
                  ts="2026-01-01T00:00:01.000000+00:00")

        fleet = sidebar_model.build_model([self.repo])
        feature = fleet.repos[0].features[0]
        self.assertEqual(feature.phase, "designing")
        self.assertIsNone(feature.phase_tick)
        self.assertEqual(feature.progress_pct, 25)

    def test_phase_with_tick_computes_pct(self):
        self._architect("arch-ph2", "feat-ph2")
        self._put("arch-ph2", "arch-ph2-p", "arch-ph2", "orchid:phase:building:2/3",
                  ts="2026-01-01T00:00:01.000000+00:00")

        fleet = sidebar_model.build_model([self.repo])
        feature = fleet.repos[0].features[0]
        self.assertEqual(feature.phase, "building")
        self.assertEqual(feature.phase_tick, (2, 3))
        # base 40 + span 45 * 2/3 = 40 + 30 = 70
        self.assertEqual(feature.progress_pct, 70)

    def test_finished_lifecycle_overrides_pct_to_100(self):
        self._architect("arch-ph3", "feat-ph3")
        self._put("arch-ph3", "arch-ph3-p", "arch-ph3", "orchid:phase:scoping",
                  ts="2026-01-01T00:00:01.000000+00:00")
        self._put("arch-ph3", "arch-ph3-lc", "arch-ph3",
                  lifecycle_body("finished", feature_id="feat-ph3"),
                  ts="2026-01-01T00:00:02.000000+00:00")

        fleet = sidebar_model.build_model([self.repo])
        feature = fleet.repos[0].features[0]
        self.assertEqual(feature.progress_pct, 100)

    def test_invalid_phase_string_is_ignored(self):
        self._architect("arch-ph4", "feat-ph4")
        self._put("arch-ph4", "arch-ph4-p", "arch-ph4", "orchid:phase:bogus",
                  ts="2026-01-01T00:00:01.000000+00:00")

        fleet = sidebar_model.build_model([self.repo])
        feature = fleet.repos[0].features[0]
        self.assertIsNone(feature.phase)
        self.assertIsNone(feature.progress_pct)


class SubagentQueueTests(_BusFixtureTestCase):
    def test_queue_then_start_moves_from_queued_to_running(self):
        self._architect("arch-q1", "feat-q1")
        self._put("arch-q1", "arch-q1-1", "arch-q1", "orchid:subagent:queue:build-1",
                  ts="2026-01-01T00:00:01.000000+00:00")
        self._put("arch-q1", "arch-q1-2", "arch-q1", "orchid:subagent:start:build-1",
                  ts="2026-01-01T00:00:02.000000+00:00")

        fleet = sidebar_model.build_model([self.repo])
        feature = fleet.repos[0].features[0]
        self.assertEqual(feature.subagents_queued, 0)
        self.assertEqual(feature.subagents_running, 1)

    def test_start_without_prior_queue_adds_directly_to_running(self):
        self._architect("arch-q2", "feat-q2")
        self._put("arch-q2", "arch-q2-1", "arch-q2", "orchid:subagent:start:build-2",
                  ts="2026-01-01T00:00:01.000000+00:00")

        fleet = sidebar_model.build_model([self.repo])
        feature = fleet.repos[0].features[0]
        self.assertEqual(feature.subagents_queued, 0)
        self.assertEqual(feature.subagents_running, 1)

    def test_queue_only_counted_until_started(self):
        self._architect("arch-q3", "feat-q3")
        self._put("arch-q3", "arch-q3-1", "arch-q3", "orchid:subagent:queue:build-3",
                  ts="2026-01-01T00:00:01.000000+00:00")

        fleet = sidebar_model.build_model([self.repo])
        feature = fleet.repos[0].features[0]
        self.assertEqual(feature.subagents_queued, 1)
        self.assertEqual(feature.subagents_running, 0)

    def test_done_removes_from_both_queued_and_running(self):
        self._architect("arch-q4", "feat-q4")
        self._put("arch-q4", "arch-q4-1", "arch-q4", "orchid:subagent:queue:build-4",
                  ts="2026-01-01T00:00:01.000000+00:00")
        self._put("arch-q4", "arch-q4-2", "arch-q4", "orchid:subagent:start:build-4",
                  ts="2026-01-01T00:00:02.000000+00:00")
        self._put("arch-q4", "arch-q4-3", "arch-q4", "orchid:subagent:done:build-4",
                  ts="2026-01-01T00:00:03.000000+00:00")

        fleet = sidebar_model.build_model([self.repo])
        feature = fleet.repos[0].features[0]
        self.assertEqual(feature.subagents_queued, 0)
        self.assertEqual(feature.subagents_running, 0)


class OpenQuestionsTests(_BusFixtureTestCase):
    def test_ask_opens_a_question(self):
        self._architect("arch-oq1", "feat-oq1")
        self._put_ask("arch-oq1", "arch-oq1-ask", "arch-oq1", "q-1",
                      "Proceed with deploy?", ts="2026-01-01T00:00:01.000000+00:00")

        fleet = sidebar_model.build_model([self.repo])
        feature = fleet.repos[0].features[0]
        self.assertEqual(feature.question_count, 1)
        self.assertEqual(feature.first_question_subject, "Proceed with deploy?")
        self.assertEqual(
            [(q.question_id, q.subject) for q in feature.open_questions],
            [("q-1", "Proceed with deploy?")],
        )
        self.assertEqual(feature.interrupt, "question")

    def test_matching_reply_clears_the_question(self):
        self._architect("arch-oq2", "feat-oq2")
        self._put_ask("arch-oq2", "arch-oq2-ask", "arch-oq2", "q-2",
                      "Ship it?", ts="2026-01-01T00:00:01.000000+00:00")
        self._put_reply("arch-oq2", "arch-oq2-reply", "operator-1", "q-2",
                        ts="2026-01-01T00:00:02.000000+00:00")

        fleet = sidebar_model.build_model([self.repo])
        feature = fleet.repos[0].features[0]
        self.assertEqual(feature.question_count, 0)
        self.assertEqual(feature.open_questions, [])
        self.assertNotEqual(feature.interrupt, "question")

    def test_askers_next_status_clears_the_question(self):
        # mirrors how last_notify_user clears today: a fresh, non-notify
        # status/activity signal from the SAME sender supersedes the wait.
        self._architect("arch-oq3", "feat-oq3")
        self._put_ask("arch-oq3", "arch-oq3-ask", "arch-oq3", "q-3",
                      "Continue?", ts="2026-01-01T00:00:01.000000+00:00")
        self._put("arch-oq3", "arch-oq3-status", "arch-oq3", "orchid:status:building",
                  ts="2026-01-01T00:00:02.000000+00:00")

        fleet = sidebar_model.build_model([self.repo])
        feature = fleet.repos[0].features[0]
        self.assertEqual(feature.question_count, 0)
        self.assertEqual(feature.status_word, "building")


class InterruptDerivationTests(_BusFixtureTestCase):
    def test_none_by_default(self):
        self._architect("arch-int1", "feat-int1")

        fleet = sidebar_model.build_model([self.repo])
        self.assertEqual(fleet.repos[0].features[0].interrupt, "none")

    def test_question_when_open_questions_present(self):
        self._architect("arch-int2", "feat-int2")
        self._put_ask("arch-int2", "arch-int2-ask", "arch-int2", "q-int2",
                      "Deploy?", ts="2026-01-01T00:00:01.000000+00:00")

        fleet = sidebar_model.build_model([self.repo])
        self.assertEqual(fleet.repos[0].features[0].interrupt, "question")

    def test_succeeded_on_pre_terminal_done_lifecycle(self):
        self._architect("arch-int3", "feat-int3")
        self._put("arch-int3", "arch-int3-lc", "arch-int3",
                  lifecycle_body("done", feature_id="feat-int3"),
                  ts="2026-01-01T00:00:01.000000+00:00")

        fleet = sidebar_model.build_model([self.repo])
        self.assertEqual(fleet.repos[0].features[0].interrupt, "succeeded")

    def test_succeeded_on_finished_lifecycle(self):
        self._architect("arch-int4", "feat-int4")
        self._put("arch-int4", "arch-int4-lc", "arch-int4",
                  lifecycle_body("finished", feature_id="feat-int4"),
                  ts="2026-01-01T00:00:01.000000+00:00")

        fleet = sidebar_model.build_model([self.repo])
        self.assertEqual(fleet.repos[0].features[0].interrupt, "succeeded")

    def test_failed_on_abandoned(self):
        self._architect("arch-int5", "feat-int5")
        self._put("arch-int5", "arch-int5-lc", "arch-int5",
                  lifecycle_body("abandoned", feature_id="feat-int5"),
                  ts="2026-01-01T00:00:01.000000+00:00")

        fleet = sidebar_model.build_model([self.repo])
        self.assertEqual(fleet.repos[0].features[0].interrupt, "failed")

    def test_failed_on_blocked_with_notify(self):
        self._architect("arch-int6", "feat-int6")
        self._put("arch-int6", "arch-int6-lc", "arch-int6",
                  lifecycle_body("blocked", feature_id="feat-int6"),
                  ts="2026-01-01T00:00:01.000000+00:00", notify_user=True)

        fleet = sidebar_model.build_model([self.repo])
        self.assertEqual(fleet.repos[0].features[0].interrupt, "failed")

    def test_none_on_blocked_without_notify(self):
        self._architect("arch-int7", "feat-int7")
        self._put("arch-int7", "arch-int7-lc", "arch-int7",
                  lifecycle_body("blocked", feature_id="feat-int7"),
                  ts="2026-01-01T00:00:01.000000+00:00")

        fleet = sidebar_model.build_model([self.repo])
        self.assertEqual(fleet.repos[0].features[0].interrupt, "none")


class DuplicateMessageDedupTests(_BusFixtureTestCase):
    """Item 7: a message identical in body+notify_user to the SENDER's
    previous one changes nothing and re-raises no notify."""

    def test_identical_consecutive_status_messages_stay_idempotent(self):
        self._architect("arch-dd1", "feat-dd1")
        self._put("arch-dd1", "arch-dd1-1", "arch-dd1", "orchid:status:waiting for input",
                  ts="2026-01-01T00:00:01.000000+00:00", notify_user=True)
        self._put("arch-dd1", "arch-dd1-2", "arch-dd1", "orchid:status:waiting for input",
                  ts="2026-01-01T00:00:02.000000+00:00", notify_user=True)

        fleet = sidebar_model.build_model([self.repo])
        feature = fleet.repos[0].features[0]
        self.assertEqual(feature.status_word, "waiting for input")
        self.assertTrue(feature.waiting_on_operator)

    def test_resent_duplicate_ask_after_reply_does_not_reopen_question(self):
        # the duplicate-summons defect: a stale, at-least-once-delivered
        # resend of the SAME ask (identical body+notify, same sender)
        # arriving after the question was already answered must not reopen it.
        self._architect("arch-dd2", "feat-dd2")
        self._put_ask("arch-dd2", "ask-1", "arch-dd2", "q-dd2", "Ship now?",
                      ts="2026-01-01T00:00:01.000000+00:00")
        self._put_reply("arch-dd2", "reply-1", "operator-x", "q-dd2",
                        ts="2026-01-01T00:00:02.000000+00:00")
        self._put_ask("arch-dd2", "ask-1-retry", "arch-dd2", "q-dd2", "Ship now?",
                      ts="2026-01-01T00:00:03.000000+00:00")

        fleet = sidebar_model.build_model([self.repo])
        feature = fleet.repos[0].features[0]
        self.assertEqual(feature.question_count, 0)
        self.assertEqual(feature.interrupt, "none")


if __name__ == "__main__":
    unittest.main()
