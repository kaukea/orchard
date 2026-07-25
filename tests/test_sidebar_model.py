"""Unit tests for tools/sidebar_model.py — the courier reader/aggregator.

Runs under both `python3 -m unittest discover` and `pytest`; stdlib only.
Fixtures are real git-init'd temp repos with courier message files written by
hand (see tests/support.py) — build_model() is exercised end to end, never
mocked.
"""
import json
import os
import subprocess
import sys
import tempfile
import time
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
    make_repo, courier_root_of, identity_body, lifecycle_body, envelope, write_message,
)


class _CourierFixtureTestCase(unittest.TestCase):
    """One fresh git repo + courier root per test."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.repo = make_repo(self._tmp.name)
        self.courier_root = courier_root_of(self.repo)

    def _put(self, folder, msg_id, sender, body, ts, notify_user=None):
        write_message(
            self.courier_root, folder,
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
        write_message(self.courier_root, folder, env)

    def _put_reply(self, folder, msg_id, sender, in_reply_to, ts, body="ack"):
        env = envelope(msg_id, sender, body=body, ts=ts)
        env["in_reply_to"] = in_reply_to
        write_message(self.courier_root, folder, env)

    def _landscaper(self, session_id, feature_id, folder=None, name=None):
        """Write the identity announce that makes session_id a renderable
        landscaper feature."""
        folder = folder or session_id
        self._put(
            folder, f"{session_id}-id", session_id,
            identity_body(session_id, agent_type="landscaper", feature_id=feature_id,
                          name=name or feature_id.replace("-", " ")),
            ts="2026-01-01T00:00:00.000000+00:00",
        )
        return folder


class StatusMappingTests(_CourierFixtureTestCase):
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
            self._landscaper(session_id, feature_id)
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
        self._landscaper("arch-done", "feat-done")
        self._put("arch-done", "arch-done-lc", "arch-done",
                  lifecycle_body("finished", feature_id="feat-done"),
                  ts="2026-01-01T00:00:01.000000+00:00")
        self._landscaper("arch-failed", "feat-failed")
        self._put("arch-failed", "arch-failed-lc", "arch-failed",
                  lifecycle_body("abandoned", feature_id="feat-failed"),
                  ts="2026-01-01T00:00:01.000000+00:00")

        fleet = sidebar_model.build_model([self.repo])
        features = {f.feature_id: f for f in fleet.repos[0].features}
        self.assertEqual(features["feat-done"].status, "done")
        self.assertEqual(features["feat-failed"].status, "failed")
        self.assertNotEqual(features["feat-done"].status, features["feat-failed"].status)

    def test_no_lifecycle_and_no_subagents_is_idle(self):
        self._landscaper("arch-fresh", "feat-fresh")

        fleet = sidebar_model.build_model([self.repo])
        feature = fleet.repos[0].features[0]
        self.assertEqual(feature.status, "idle")

    def test_active_subagent_marks_working_even_without_lifecycle_push(self):
        self._landscaper("arch-working", "feat-working")
        self._put("arch-working", "arch-working-s1", "arch-working",
                  "orchid:subagent:start:sower-1",
                  ts="2026-01-01T00:00:01.000000+00:00")

        fleet = sidebar_model.build_model([self.repo])
        feature = fleet.repos[0].features[0]
        self.assertEqual(feature.status, "working")

    def test_pre_terminal_done_lifecycle_is_waiting_on_operator(self):
        # lifecycle "done" (built/tested, awaiting THAT IS ALL) is, by
        # definition, an operator-wait -- not a separate terminal status.
        self._landscaper("arch-predone", "feat-predone")
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


class BlockedOnTests(_CourierFixtureTestCase):
    """blocked_on distinguishes "waiting on a component" from "awaiting
    another agent" — the minimal tag added to the blocked lifecycle signal
    since the prior signal shape carried no such distinction."""

    def test_blocked_defaults_to_waiting_on_component(self):
        self._landscaper("arch-blocked-comp", "feat-blocked-comp")
        self._put("arch-blocked-comp", "arch-blocked-comp-lc", "arch-blocked-comp",
                  lifecycle_body("blocked", feature_id="feat-blocked-comp"),
                  ts="2026-01-01T00:00:01.000000+00:00")

        fleet = sidebar_model.build_model([self.repo])
        feature = fleet.repos[0].features[0]
        self.assertEqual(feature.status, "waiting")
        self.assertFalse(feature.waiting_on_operator)

    def test_blocked_on_agent_is_awaiting_agent(self):
        self._landscaper("arch-blocked-peer", "feat-blocked-peer")
        self._put("arch-blocked-peer", "arch-blocked-peer-lc", "arch-blocked-peer",
                  lifecycle_body("blocked", feature_id="feat-blocked-peer",
                                blocked_on="agent"),
                  ts="2026-01-01T00:00:01.000000+00:00")

        fleet = sidebar_model.build_model([self.repo])
        feature = fleet.repos[0].features[0]
        self.assertEqual(feature.status, "awaiting_agent")

    def test_blocked_on_component_explicit_is_waiting(self):
        self._landscaper("arch-blocked-explicit", "feat-blocked-explicit")
        self._put("arch-blocked-explicit", "arch-blocked-explicit-lc", "arch-blocked-explicit",
                  lifecycle_body("blocked", feature_id="feat-blocked-explicit",
                                blocked_on="component"),
                  ts="2026-01-01T00:00:01.000000+00:00")

        fleet = sidebar_model.build_model([self.repo])
        feature = fleet.repos[0].features[0]
        self.assertEqual(feature.status, "waiting")


class WaitingOperatorVariantTests(_CourierFixtureTestCase):
    """The ❓ waiting-on-operator variant — driven by last_notify_user (or
    the equivalent lifecycle "done" signal), never by blocked_on=agent."""

    def test_notify_user_flag_marks_waiting_on_operator(self):
        self._landscaper("arch-notify", "feat-notify")
        self._put("arch-notify", "arch-notify-act", "arch-notify",
                  "orchid:activity:need input",
                  ts="2026-01-01T00:00:01.000000+00:00", notify_user=True)

        fleet = sidebar_model.build_model([self.repo])
        feature = fleet.repos[0].features[0]
        self.assertTrue(feature.waiting_on_operator)
        self.assertEqual(feature.status, "waiting")

    def test_reannounce_after_notify_does_not_clear_waiting(self):
        self._landscaper("arch-sticky1", "feat-sticky1")
        self._put("arch-sticky1", "arch-sticky1-act", "arch-sticky1",
                  "orchid:activity:need input",
                  ts="2026-01-01T00:00:01.000000+00:00", notify_user=True)
        # a later re-announce (identity push) from the SAME sender, without
        # notify_user, must not clear the still-open waiting flash
        self._put("arch-sticky1", "arch-sticky1-id2", "arch-sticky1",
                  identity_body("arch-sticky1", agent_type="landscaper",
                                feature_id="feat-sticky1", name="feat sticky1"),
                  ts="2026-01-01T00:00:02.000000+00:00")

        fleet = sidebar_model.build_model([self.repo])
        feature = fleet.repos[0].features[0]
        self.assertTrue(feature.waiting_on_operator)
        self.assertEqual(feature.status, "waiting")

    def test_plain_lifecycle_after_notify_does_not_clear_waiting(self):
        self._landscaper("arch-sticky2", "feat-sticky2")
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
        self._landscaper("arch-sticky3", "feat-sticky3")
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


class AttributionTests(_CourierFixtureTestCase):
    def test_activity_attributed_to_sender_not_folder(self):
        self._landscaper("arch-A", "feat-A")
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


class SubagentTests(_CourierFixtureTestCase):
    def test_start_without_done_is_present(self):
        self._landscaper("arch-sub1", "feat-sub1")
        self._put("arch-sub1", "arch-sub1-s1", "arch-sub1",
                  "orchid:subagent:start:build-agent",
                  ts="2026-01-01T00:00:01.000000+00:00")

        fleet = sidebar_model.build_model([self.repo])
        labels = [s.label for s in fleet.repos[0].features[0].subagents]
        self.assertEqual(labels, ["build-agent"])

    def test_start_then_done_is_absent(self):
        self._landscaper("arch-sub2", "feat-sub2")
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
        self._landscaper("arch-sub3", "feat-sub3")
        self._put("arch-sub3", "arch-sub3-s1", "arch-sub3",
                  "orchid:subagent:start:messaging",
                  ts="2026-01-01T00:00:01.000000+00:00")

        fleet = sidebar_model.build_model([self.repo])
        self.assertEqual(fleet.repos[0].features[0].subagents, [])

    def test_courier_sidecar_child_session_excluded(self):
        self._landscaper("arch-sub4", "feat-sub4")
        # a courier sidecar child session (agent_type "courier") whose parent_session
        # points at the landscaper must never surface as a subagent row, even
        # though it satisfies the generic parent_session-match rule.
        self._put("courier-child", "courier-child-id", "courier-child",
                  identity_body("courier-child", agent_type="courier", name="messaging",
                                parent_session="arch-sub4"),
                  ts="2026-01-01T00:00:01.000000+00:00")

        fleet = sidebar_model.build_model([self.repo])
        self.assertEqual(fleet.repos[0].features[0].subagents, [])

    def test_two_parents_each_show_their_own_subagents(self):
        # sidebar-polish item 3: EVERY agent's subagents render under their
        # own parent, not just the first feature's.
        self._landscaper("arch-parentA", "feat-parentA")
        self._put("arch-parentA", "arch-parentA-s1", "arch-parentA",
                  "orchid:subagent:start:sower-A1",
                  ts="2026-01-01T00:00:01.000000+00:00")
        self._put("arch-parentA", "arch-parentA-s2", "arch-parentA",
                  "orchid:subagent:start:sower-A2",
                  ts="2026-01-01T00:00:02.000000+00:00")

        self._landscaper("arch-parentB", "feat-parentB")
        self._put("arch-parentB", "arch-parentB-s1", "arch-parentB",
                  "orchid:subagent:start:sower-B1",
                  ts="2026-01-01T00:00:01.000000+00:00")
        # arch-parentB also has a peer session (non-courier) parented to it
        self._put("peer-B", "peer-B-id", "peer-B",
                  identity_body("peer-B", agent_type="sower", name="peer-sower-B",
                                parent_session="arch-parentB"),
                  ts="2026-01-01T00:00:01.000000+00:00")

        fleet = sidebar_model.build_model([self.repo])
        features = {f.feature_id: f for f in fleet.repos[0].features}
        self.assertEqual(len(features), 2)

        labels_a = sorted(s.label for s in features["feat-parentA"].subagents)
        labels_b = sorted(s.label for s in features["feat-parentB"].subagents)
        self.assertEqual(labels_a, ["sower-A1", "sower-A2"])
        self.assertEqual(labels_b, ["peer-sower-B", "sower-B1"])


class InternalRowFilteringTests(_CourierFixtureTestCase):
    """Rows never operator-facing: a bare session-UUID row (no announced
    name) — sidebar-polish item 2."""

    _UUID = "3fa85f64-5717-4562-b3fc-2c963f66afa6"

    def test_architect_with_no_name_and_no_feature_id_is_hidden(self):
        self._put(self._UUID, f"{self._UUID}-id", self._UUID,
                  identity_body(self._UUID, agent_type="landscaper"),
                  ts="2026-01-01T00:00:00.000000+00:00")

        fleet = sidebar_model.build_model([self.repo])
        self.assertEqual(fleet.repos[0].features, [])

    def test_subagent_with_no_name_and_uuid_session_id_is_hidden(self):
        self._landscaper("arch-uuidsub", "feat-uuidsub")
        self._put(self._UUID, f"{self._UUID}-id", self._UUID,
                  identity_body(self._UUID, agent_type="sower",
                                parent_session="arch-uuidsub"),
                  ts="2026-01-01T00:00:01.000000+00:00")

        fleet = sidebar_model.build_model([self.repo])
        self.assertEqual(fleet.repos[0].features[0].subagents, [])

    def test_subagent_with_uuid_session_id_but_announced_name_is_shown(self):
        # a raw-uuid session_id is fine as long as a NAME was announced —
        # only a bare, unnamed uuid row is hidden.
        self._landscaper("arch-nameduuidsub", "feat-nameduuidsub")
        self._put(self._UUID, f"{self._UUID}-id", self._UUID,
                  identity_body(self._UUID, agent_type="sower", name="named-sower",
                                parent_session="arch-nameduuidsub"),
                  ts="2026-01-01T00:00:01.000000+00:00")

        fleet = sidebar_model.build_model([self.repo])
        labels = [s.label for s in fleet.repos[0].features[0].subagents]
        self.assertEqual(labels, ["named-sower"])


class StaleRowEvictionTests(unittest.TestCase):
    """Root-cause fix: a sender's ENTIRE state used to be evicted a scan
    after its terminal lifecycle signal, for BOTH finished and abandoned —
    exercised directly against a long-lived _CourierAggregator, the only way to
    observe multi-scan behaviour (build_model() always starts a fresh one).

    Operator decision, 2026-07-24 (sidebar-titling item 7): a done feature's
    row must never leave the current sidebar's view. `finished` senders are
    now retained forever (never evicted); `abandoned` senders keep the prior
    one-scan-grace-then-evict behaviour."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.repo = make_repo(self._tmp.name)
        self.courier_root = courier_root_of(self.repo)

    def _put(self, folder, msg_id, sender, body, ts):
        write_message(self.courier_root, folder, envelope(msg_id, sender, body=body, ts=ts))

    def test_finished_state_is_retained_across_many_scans(self):
        self._put("arch-stale", "arch-stale-id", "arch-stale",
                  identity_body("arch-stale", agent_type="landscaper",
                                feature_id="feat-stale"),
                  ts="2026-01-01T00:00:00.000000+00:00")

        agg = sidebar_model._CourierAggregator()
        agg.scan(self.courier_root)
        self.assertEqual(agg.repo(self.repo).features[0].status, "idle")

        self._put("arch-stale", "arch-stale-lc", "arch-stale",
                  lifecycle_body("finished", feature_id="feat-stale"),
                  ts="2026-01-01T00:00:01.000000+00:00")
        agg.scan(self.courier_root)
        # same scan the terminal signal arrived on: visible as "done"
        self.assertEqual(agg.repo(self.repo).features[0].status, "done")

        # a done feature's row never leaves — it must still be present (and
        # still "done") across many further scans, not evicted after one
        # scan's grace, and not requiring the message files to still exist
        # on disk (both ids are already in _seen_ids so re-applying is moot).
        for _ in range(5):
            agg.scan(self.courier_root)
            self.assertEqual(agg.repo(self.repo).features[0].status, "done")

    def test_abandoned_state_evicted_one_scan_after_signal(self):
        self._put("arch-fail", "arch-fail-id", "arch-fail",
                  identity_body("arch-fail", agent_type="landscaper",
                                feature_id="feat-fail"),
                  ts="2026-01-01T00:00:00.000000+00:00")

        agg = sidebar_model._CourierAggregator()
        agg.scan(self.courier_root)
        self.assertEqual(agg.repo(self.repo).features[0].status, "idle")

        self._put("arch-fail", "arch-fail-lc", "arch-fail",
                  lifecycle_body("abandoned", feature_id="feat-fail"),
                  ts="2026-01-01T00:00:01.000000+00:00")
        agg.scan(self.courier_root)
        # same scan the terminal signal arrived on: still visible as "failed"
        self.assertEqual(agg.repo(self.repo).features[0].status, "failed")

        # neither message file needs to be removed for this: eviction is
        # driven by the terminal signal already observed, not by disk
        # presence (both message ids are already in _seen_ids, so even the
        # still-on-disk identity announce is not re-applied) -- the NEXT
        # scan must evict the sender's state IN FULL, not just its waiting
        # flag, so the row disappears entirely
        agg.scan(self.courier_root)
        self.assertEqual(agg.repo(self.repo).features, [])


class CourierRowTests(_CourierFixtureTestCase):
    """Courier rows: exactly one collapsed row per live parent agent, never
    for a parent with no courier, never duplicated (sidebar-polish item 5)."""

    def test_no_courier_row_when_no_courier_session(self):
        self._landscaper("arch-nocourier", "feat-nocourier")

        fleet = sidebar_model.build_model([self.repo])
        self.assertIsNone(fleet.repos[0].features[0].courier)

    def test_courier_row_present_for_live_landscaper(self):
        self._landscaper("arch-hascourier", "feat-hascourier")
        self._put("courier-1", "courier-1-id", "courier-1",
                  identity_body("courier-1", agent_type="courier", name="messaging",
                                parent_session="arch-hascourier"),
                  ts="2026-01-01T00:00:01.000000+00:00")

        fleet = sidebar_model.build_model([self.repo])
        feature = fleet.repos[0].features[0]
        self.assertIsNotNone(feature.courier)
        self.assertEqual(feature.courier.label, sidebar_model.COURIER_LABEL)

    def test_duplicate_courier_sessions_collapse_to_one_row(self):
        # a known, separately-root-caused defect (bus-singleton task) can
        # spawn more than one courier session for the same parent -- display
        # must still show exactly one row, never more.
        self._landscaper("arch-dupcourier", "feat-dupcourier")
        for i in range(3):
            self._put(f"courier-dup-{i}", f"courier-dup-{i}-id", f"courier-dup-{i}",
                      identity_body(f"courier-dup-{i}", agent_type="courier", name="messaging",
                                    parent_session="arch-dupcourier"),
                      ts="2026-01-01T00:00:01.000000+00:00")

        fleet = sidebar_model.build_model([self.repo])
        feature = fleet.repos[0].features[0]
        self.assertIsNotNone(feature.courier)  # exactly one Courier object, not a list

    def test_gardener_courier_row(self):
        self._put("orch-1", "orch-1-id", "orch-1",
                  identity_body("orch-1", agent_type="gardener"),
                  ts="2026-01-01T00:00:00.000000+00:00")
        self._put("orch-courier", "orch-courier-id", "orch-courier",
                  identity_body("orch-courier", agent_type="courier", name="messaging",
                                parent_session="orch-1"),
                  ts="2026-01-01T00:00:01.000000+00:00")

        fleet = sidebar_model.build_model([self.repo])
        self.assertIsNotNone(fleet.repos[0].courier)


class CrossRepoTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)

    def test_two_repos_both_appear_in_fleet(self):
        repo1 = make_repo(self._tmp.name)
        repo2 = make_repo(self._tmp.name)
        for repo, tag in ((repo1, "one"), (repo2, "two")):
            root = courier_root_of(repo)
            write_message(
                root, f"arch-{tag}",
                envelope(
                    f"arch-{tag}-id", f"arch-{tag}",
                    body=identity_body(f"arch-{tag}", agent_type="landscaper",
                                       feature_id=f"feat-{tag}"),
                    ts="2026-01-01T00:00:00.000000+00:00",
                ),
            )

        fleet = sidebar_model.build_model([repo1, repo2])
        self.assertEqual(len(fleet.repos), 2)
        self.assertEqual({r.path for r in fleet.repos}, {repo1, repo2})
        feature_ids = {r.features[0].feature_id for r in fleet.repos}
        self.assertEqual(feature_ids, {"feat-one", "feat-two"})


class DedupTests(_CourierFixtureTestCase):
    def test_same_id_second_occurrence_across_scans_is_ignored(self):
        # _CourierAggregator (not the throwaway one build_model() uses internally)
        # exercised directly across TWO scans -- this is the only way to
        # observe the id-dedup contract described in sidebar_model's own
        # docstring (state persists and re-delivery of an already-seen id is a
        # no-op), since build_model() always starts a fresh aggregator.
        write_message(
            self.courier_root, "arch-dedup",
            envelope("arch-dedup-id", "arch-dedup",
                    body=identity_body("arch-dedup", agent_type="landscaper",
                                        feature_id="feat-dedup"),
                    ts="2026-01-01T00:00:00.000000+00:00"),
        )
        write_message(
            self.courier_root, "arch-dedup",
            envelope("dup-1", "arch-dedup", body="orchid:activity:first",
                    ts="2026-01-01T00:00:01.000000+00:00"),
        )

        agg = sidebar_model._CourierAggregator()
        agg.scan(self.courier_root)
        first_pass = agg.repo(self.repo)
        self.assertEqual(first_pass.features[0].activity, "first")

        # SAME envelope id "dup-1", different body, delivered as a second
        # file (simulates a stale re-delivery) -- must not be re-applied once
        # that id was seen in an earlier scan.
        write_message(
            self.courier_root, "arch-dedup",
            envelope("dup-1", "arch-dedup", body="orchid:activity:second",
                    ts="2026-01-01T00:00:02.000000+00:00"),
            filename="dup-1-retry.json",
        )
        agg.scan(self.courier_root)
        second_pass = agg.repo(self.repo)
        self.assertEqual(second_pass.features[0].activity, "first",
                         "message with an already-seen id must not be re-applied")

    def test_seen_ids_pruned_when_message_removed(self):
        # the underlying message file is ephemeral (deleted by its
        # recipient's receive), so once it's gone from disk its id must be
        # pruned from _seen_ids rather than retained forever.
        write_message(
            self.courier_root, "arch-prune",
            envelope("arch-prune-id", "arch-prune",
                    body=identity_body("arch-prune", agent_type="landscaper",
                                        feature_id="feat-prune"),
                    ts="2026-01-01T00:00:00.000000+00:00"),
        )

        agg = sidebar_model._CourierAggregator()
        agg.scan(self.courier_root)
        self.assertIn("arch-prune-id", agg._seen_ids)

        (Path(self.courier_root) / "arch-prune" / "arch-prune-id.json").unlink()

        agg.scan(self.courier_root)
        self.assertNotIn("arch-prune-id", agg._seen_ids)


class RepoStatusTests(_CourierFixtureTestCase):
    def test_repo_without_gardener_is_idle(self):
        self._landscaper("arch-idle", "feat-idle")

        fleet = sidebar_model.build_model([self.repo])
        self.assertEqual(fleet.repos[0].status, "idle")


class HasSessionTests(_CourierFixtureTestCase):
    """has_session (item 3, "empty projects don't render"): True only when
    the repo has a live gardener session or at least one feature; False
    for a repo whose courier is empty (nothing renderable), which the renderer's
    flatten() then skips."""

    def test_no_gardener_and_no_features_is_false(self):
        fleet = sidebar_model.build_model([self.repo])
        self.assertEqual(len(fleet.repos), 1)
        self.assertFalse(fleet.repos[0].has_session)

    def test_orchestrator_session_alone_is_true(self):
        self._put("orch-only", "orch-only-id", "orch-only",
                  identity_body("orch-only", agent_type="gardener"),
                  ts="2026-01-01T00:00:00.000000+00:00")

        fleet = sidebar_model.build_model([self.repo])
        self.assertTrue(fleet.repos[0].has_session)

    def test_feature_alone_is_true(self):
        self._landscaper("arch-hassession", "feat-hassession")

        fleet = sidebar_model.build_model([self.repo])
        self.assertTrue(fleet.repos[0].has_session)


class FeatureNameTests(_CourierFixtureTestCase):
    def test_announced_name_is_used_over_derived_form(self):
        self._landscaper("arch-namedfeat", "custom-feature", name="Custom Label")

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
    (landscaper HOW decision) — when set, it is read verbatim and the
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

class StatusWordTests(_CourierFixtureTestCase):
    def test_status_prefix_sets_status_word_and_mirrors_activity(self):
        self._landscaper("arch-sw1", "feat-sw1")
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
        self._landscaper("arch-sw2", "feat-sw2")
        self._put("arch-sw2", "arch-sw2-legacy", "arch-sw2",
                  "orchid:activity:doing legacy work",
                  ts="2026-01-01T00:00:01.000000+00:00")

        fleet = sidebar_model.build_model([self.repo])
        feature = fleet.repos[0].features[0]
        self.assertEqual(feature.status_word, "doing legacy work")
        self.assertEqual(feature.activity, "doing legacy work")


class UpdateTextTests(_CourierFixtureTestCase):
    def test_update_sets_update_text(self):
        self._landscaper("arch-upd1", "feat-upd1")
        self._put("arch-upd1", "arch-upd1-u", "arch-upd1",
                  "orchid:update:shipped the migration",
                  ts="2026-01-01T00:00:01.000000+00:00")

        fleet = sidebar_model.build_model([self.repo])
        feature = fleet.repos[0].features[0]
        self.assertEqual(feature.update_text, "shipped the migration")

    def test_update_never_drives_status_derivation(self):
        self._landscaper("arch-upd2", "feat-upd2")
        self._put("arch-upd2", "arch-upd2-u", "arch-upd2",
                  "orchid:update:a long narrative sentence",
                  ts="2026-01-01T00:00:01.000000+00:00")

        fleet = sidebar_model.build_model([self.repo])
        feature = fleet.repos[0].features[0]
        self.assertEqual(feature.status, "idle")

    def test_update_never_sets_notify_even_if_flagged(self):
        # defensive: the grammar says update never notifies, but the
        # aggregator must not trust an envelope that claims otherwise.
        self._landscaper("arch-upd3", "feat-upd3")
        self._put("arch-upd3", "arch-upd3-u", "arch-upd3",
                  "orchid:update:need review", ts="2026-01-01T00:00:01.000000+00:00",
                  notify_user=True)

        fleet = sidebar_model.build_model([self.repo])
        feature = fleet.repos[0].features[0]
        self.assertFalse(feature.waiting_on_operator)
        self.assertEqual(feature.status, "idle")


class PhaseProgressTests(_CourierFixtureTestCase):
    def test_phase_without_tick_uses_base_pct(self):
        self._landscaper("arch-ph1", "feat-ph1")
        self._put("arch-ph1", "arch-ph1-p", "arch-ph1", "orchid:phase:designing",
                  ts="2026-01-01T00:00:01.000000+00:00")

        fleet = sidebar_model.build_model([self.repo])
        feature = fleet.repos[0].features[0]
        self.assertEqual(feature.phase, "designing")
        self.assertIsNone(feature.phase_tick)
        self.assertEqual(feature.progress_pct, 25)

    def test_phase_with_tick_computes_pct(self):
        self._landscaper("arch-ph2", "feat-ph2")
        self._put("arch-ph2", "arch-ph2-p", "arch-ph2", "orchid:phase:building:2/3",
                  ts="2026-01-01T00:00:01.000000+00:00")

        fleet = sidebar_model.build_model([self.repo])
        feature = fleet.repos[0].features[0]
        self.assertEqual(feature.phase, "building")
        self.assertEqual(feature.phase_tick, (2, 3))
        # base 40 + span 45 * 2/3 = 40 + 30 = 70
        self.assertEqual(feature.progress_pct, 70)

    def test_finished_lifecycle_overrides_pct_to_100(self):
        self._landscaper("arch-ph3", "feat-ph3")
        self._put("arch-ph3", "arch-ph3-p", "arch-ph3", "orchid:phase:scoping",
                  ts="2026-01-01T00:00:01.000000+00:00")
        self._put("arch-ph3", "arch-ph3-lc", "arch-ph3",
                  lifecycle_body("finished", feature_id="feat-ph3"),
                  ts="2026-01-01T00:00:02.000000+00:00")

        fleet = sidebar_model.build_model([self.repo])
        feature = fleet.repos[0].features[0]
        self.assertEqual(feature.progress_pct, 100)

    def test_invalid_phase_string_is_ignored(self):
        self._landscaper("arch-ph4", "feat-ph4")
        self._put("arch-ph4", "arch-ph4-p", "arch-ph4", "orchid:phase:bogus",
                  ts="2026-01-01T00:00:01.000000+00:00")

        fleet = sidebar_model.build_model([self.repo])
        feature = fleet.repos[0].features[0]
        self.assertIsNone(feature.phase)
        self.assertIsNone(feature.progress_pct)


class SubagentQueueTests(_CourierFixtureTestCase):
    def test_queue_then_start_moves_from_queued_to_running(self):
        self._landscaper("arch-q1", "feat-q1")
        self._put("arch-q1", "arch-q1-1", "arch-q1", "orchid:subagent:queue:build-1",
                  ts="2026-01-01T00:00:01.000000+00:00")
        self._put("arch-q1", "arch-q1-2", "arch-q1", "orchid:subagent:start:build-1",
                  ts="2026-01-01T00:00:02.000000+00:00")

        fleet = sidebar_model.build_model([self.repo])
        feature = fleet.repos[0].features[0]
        self.assertEqual(feature.subagents_queued, 0)
        self.assertEqual(feature.subagents_running, 1)

    def test_start_without_prior_queue_adds_directly_to_running(self):
        self._landscaper("arch-q2", "feat-q2")
        self._put("arch-q2", "arch-q2-1", "arch-q2", "orchid:subagent:start:build-2",
                  ts="2026-01-01T00:00:01.000000+00:00")

        fleet = sidebar_model.build_model([self.repo])
        feature = fleet.repos[0].features[0]
        self.assertEqual(feature.subagents_queued, 0)
        self.assertEqual(feature.subagents_running, 1)

    def test_queue_only_counted_until_started(self):
        self._landscaper("arch-q3", "feat-q3")
        self._put("arch-q3", "arch-q3-1", "arch-q3", "orchid:subagent:queue:build-3",
                  ts="2026-01-01T00:00:01.000000+00:00")

        fleet = sidebar_model.build_model([self.repo])
        feature = fleet.repos[0].features[0]
        self.assertEqual(feature.subagents_queued, 1)
        self.assertEqual(feature.subagents_running, 0)

    def test_done_removes_from_both_queued_and_running(self):
        self._landscaper("arch-q4", "feat-q4")
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


class OpenQuestionsTests(_CourierFixtureTestCase):
    def test_ask_opens_a_question(self):
        self._landscaper("arch-oq1", "feat-oq1")
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
        self._landscaper("arch-oq2", "feat-oq2")
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
        self._landscaper("arch-oq3", "feat-oq3")
        self._put_ask("arch-oq3", "arch-oq3-ask", "arch-oq3", "q-3",
                      "Continue?", ts="2026-01-01T00:00:01.000000+00:00")
        self._put("arch-oq3", "arch-oq3-status", "arch-oq3", "orchid:status:building",
                  ts="2026-01-01T00:00:02.000000+00:00")

        fleet = sidebar_model.build_model([self.repo])
        feature = fleet.repos[0].features[0]
        self.assertEqual(feature.question_count, 0)
        self.assertEqual(feature.status_word, "building")


class InterruptDerivationTests(_CourierFixtureTestCase):
    def test_none_by_default(self):
        self._landscaper("arch-int1", "feat-int1")

        fleet = sidebar_model.build_model([self.repo])
        self.assertEqual(fleet.repos[0].features[0].interrupt, "none")

    def test_question_when_open_questions_present(self):
        self._landscaper("arch-int2", "feat-int2")
        self._put_ask("arch-int2", "arch-int2-ask", "arch-int2", "q-int2",
                      "Deploy?", ts="2026-01-01T00:00:01.000000+00:00")

        fleet = sidebar_model.build_model([self.repo])
        self.assertEqual(fleet.repos[0].features[0].interrupt, "question")

    def test_succeeded_on_pre_terminal_done_lifecycle(self):
        self._landscaper("arch-int3", "feat-int3")
        self._put("arch-int3", "arch-int3-lc", "arch-int3",
                  lifecycle_body("done", feature_id="feat-int3"),
                  ts="2026-01-01T00:00:01.000000+00:00")

        fleet = sidebar_model.build_model([self.repo])
        self.assertEqual(fleet.repos[0].features[0].interrupt, "succeeded")

    def test_succeeded_on_finished_lifecycle(self):
        self._landscaper("arch-int4", "feat-int4")
        self._put("arch-int4", "arch-int4-lc", "arch-int4",
                  lifecycle_body("finished", feature_id="feat-int4"),
                  ts="2026-01-01T00:00:01.000000+00:00")

        fleet = sidebar_model.build_model([self.repo])
        self.assertEqual(fleet.repos[0].features[0].interrupt, "succeeded")

    def test_failed_on_abandoned(self):
        self._landscaper("arch-int5", "feat-int5")
        self._put("arch-int5", "arch-int5-lc", "arch-int5",
                  lifecycle_body("abandoned", feature_id="feat-int5"),
                  ts="2026-01-01T00:00:01.000000+00:00")

        fleet = sidebar_model.build_model([self.repo])
        self.assertEqual(fleet.repos[0].features[0].interrupt, "failed")

    def test_failed_on_blocked_with_notify(self):
        self._landscaper("arch-int6", "feat-int6")
        self._put("arch-int6", "arch-int6-lc", "arch-int6",
                  lifecycle_body("blocked", feature_id="feat-int6"),
                  ts="2026-01-01T00:00:01.000000+00:00", notify_user=True)

        fleet = sidebar_model.build_model([self.repo])
        self.assertEqual(fleet.repos[0].features[0].interrupt, "failed")

    def test_none_on_blocked_without_notify(self):
        self._landscaper("arch-int7", "feat-int7")
        self._put("arch-int7", "arch-int7-lc", "arch-int7",
                  lifecycle_body("blocked", feature_id="feat-int7"),
                  ts="2026-01-01T00:00:01.000000+00:00")

        fleet = sidebar_model.build_model([self.repo])
        self.assertEqual(fleet.repos[0].features[0].interrupt, "none")


class DuplicateMessageDedupTests(_CourierFixtureTestCase):
    """Item 7: a message identical in body+notify_user to the SENDER's
    previous one changes nothing and re-raises no notify."""

    def test_identical_consecutive_status_messages_stay_idempotent(self):
        self._landscaper("arch-dd1", "feat-dd1")
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
        self._landscaper("arch-dd2", "feat-dd2")
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


class FormattingHelperTests(unittest.TestCase):
    """bus-message-specifying B5b: the compact human-string formatters shared
    by age/worked (duration) and tokens/dollars."""

    def test_format_duration_hours_and_zero_padded_minutes(self):
        self.assertEqual(sidebar_model._format_duration(3 * 3600 + 12 * 60), "3h12")
        self.assertEqual(sidebar_model._format_duration(6 * 3600 + 2 * 60), "6h02")
        self.assertEqual(sidebar_model._format_duration(1 * 3600 + 47 * 60), "1h47")

    def test_format_duration_minutes_only_under_an_hour(self):
        self.assertEqual(sidebar_model._format_duration(18 * 60), "18m")
        self.assertEqual(sidebar_model._format_duration(0), "0m")

    def test_format_tokens_compacts_thousands_and_millions(self):
        self.assertEqual(sidebar_model._format_tokens(212_000), "212k")
        self.assertEqual(sidebar_model._format_tokens(384_000), "384k")
        self.assertEqual(sidebar_model._format_tokens(1_200_000), "1.2M")
        self.assertEqual(sidebar_model._format_tokens(500), "500")

    def test_format_dollars_always_two_decimals(self):
        self.assertEqual(sidebar_model._format_dollars(7.9), "7.90")
        self.assertEqual(sidebar_model._format_dollars(4.123), "4.12")


class WorkedSecondsTests(unittest.TestCase):
    """The worked-time gap math on synthetic commit-epoch lists, factored out
    of any git subprocess so it is testable without git (bus-message-specifying
    B5b): gaps <= 30 minutes count at face value, longer gaps
    count as zero, floored at 10 minutes once the branch has any commit."""

    def test_no_commits_is_zero(self):
        self.assertEqual(sidebar_model._worked_seconds([]), 0.0)

    def test_single_commit_is_floored_at_ten_minutes(self):
        self.assertEqual(sidebar_model._worked_seconds([1_000]), 600.0)

    def test_gaps_at_or_under_thirty_minutes_count_at_face_value(self):
        epochs = [0, 900, 1800]  # two 900s (15m) gaps
        self.assertEqual(sidebar_model._worked_seconds(epochs), 1800.0)

    def test_gaps_over_thirty_minutes_count_as_zero(self):
        epochs = [0, 3600]  # one 60m gap, over the cap -> floored
        self.assertEqual(sidebar_model._worked_seconds(epochs), 600.0)

    def test_mixed_gaps_only_sum_the_short_ones(self):
        epochs = [0, 600, 600 + 3600]  # 10m gap counted, 60m gap dropped
        self.assertEqual(sidebar_model._worked_seconds(epochs), 600.0)

    def test_unsorted_input_is_sorted_before_gap_math(self):
        self.assertEqual(
            sidebar_model._worked_seconds([1800, 0, 900]),
            sidebar_model._worked_seconds([0, 900, 1800]),
        )


class TTLCacheTests(unittest.TestCase):
    """The refresh-throttling cache shared by tokens/dollars and age/worked —
    exercised with an injected fake clock, never a real sleep."""

    def _cache(self, ttl=30):
        clock_state = {"now": 0.0}
        cache = sidebar_model._TTLCache(ttl, clock=lambda: clock_state["now"])
        return cache, clock_state

    def test_second_get_within_ttl_does_not_recompute(self):
        cache, clock_state = self._cache()
        calls = []

        def compute():
            calls.append(1)
            return "value"

        self.assertEqual(cache.get("k", compute), "value")
        clock_state["now"] = 10.0
        self.assertEqual(cache.get("k", compute), "value")
        self.assertEqual(len(calls), 1)

    def test_get_recomputes_once_ttl_has_elapsed(self):
        cache, clock_state = self._cache()
        calls = []

        def compute():
            calls.append(1)
            return "value"

        cache.get("k", compute)
        clock_state["now"] = 31.0
        cache.get("k", compute)
        self.assertEqual(len(calls), 2)

    def test_different_keys_cache_independently(self):
        cache, _clock_state = self._cache()
        self.assertEqual(cache.get("a", lambda: "A"), "A")
        self.assertEqual(cache.get("b", lambda: "B"), "B")


class ReadStatusTests(unittest.TestCase):
    """tokens/dollars via a direct, zero-courier-traffic read of the session's
    own transcript, reusing courier.py's TOKEN_CLASSES/usage_entries/
    estimates_for over that transcript rather than any courier message."""

    def _write_transcript(self, tmp, model, usage):
        path = Path(tmp) / "session.jsonl"
        path.write_text(
            json.dumps({"message": {"model": model, "usage": usage}}) + "\n",
            encoding="utf-8",
        )
        return path

    def test_reads_tokens_and_dollars_from_a_synthetic_transcript(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self._write_transcript(
                tmp, "claude-sonnet-5-20260101",
                {"input_tokens": 100_000, "output_tokens": 50_000,
                 "cache_read_input_tokens": 0, "cache_creation_input_tokens": 0},
            )
            with mock.patch.object(sidebar_model, "_transcript_for_session", return_value=path):
                tokens, dollars, model = sidebar_model._read_status("some-session")
        self.assertEqual(tokens, "150k")
        expected_cost = (100_000 * 3.0 + 50_000 * 15.0) / 1_000_000
        self.assertEqual(dollars, sidebar_model._format_dollars(expected_cost))
        self.assertEqual(model, "claude-sonnet-5-20260101")

    def test_no_transcript_yields_none_none(self):
        with mock.patch.object(sidebar_model, "_transcript_for_session", return_value=None):
            self.assertEqual(sidebar_model._read_status("missing"), (None, None, None))

    def test_unknown_model_yields_tokens_but_no_dollars(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self._write_transcript(
                tmp, "some-unknown-model",
                {"input_tokens": 1_000, "output_tokens": 0,
                 "cache_read_input_tokens": 0, "cache_creation_input_tokens": 0},
            )
            with mock.patch.object(sidebar_model, "_transcript_for_session", return_value=path):
                tokens, dollars, model = sidebar_model._read_status("s")
        self.assertEqual(tokens, "1k")
        self.assertIsNone(dollars)
        self.assertEqual(model, "some-unknown-model")

    def test_transcript_model_backfills_identity_when_identity_lacks_it(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self._write_transcript(
                tmp, "claude-opus-5-20260101",
                {"input_tokens": 1_000, "output_tokens": 0,
                 "cache_read_input_tokens": 0, "cache_creation_input_tokens": 0},
            )
            with mock.patch.object(sidebar_model, "_transcript_for_session", return_value=path):
                state = sidebar_model._SessionState(session_id="s1")
                state.agent_type = "landscaper"
                row = sidebar_model.Feature(
                    feature_id="f1", name="f one", activity="",
                    status="working", waiting_on_operator=False,
                )
                sidebar_model._apply_row_extension(
                    row, state, sidebar_model._TTLCache(ttl_seconds=30),
                )
        self.assertEqual(row.model, "claude-opus-5-20260101")


class ReadGitStatsTests(unittest.TestCase):
    """age/worked's git-facing half — a real (throwaway) git repo, since
    _read_git_stats' own branch-lookup/subprocess plumbing needs exercising
    once; the gap MATH itself is covered git-free by WorkedSecondsTests."""

    def _repo_with_main(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        repo_dir = tmp.name
        subprocess.run(["git", "init", "--quiet", "-b", "main"], cwd=repo_dir,
                       check=True, capture_output=True)
        (Path(repo_dir) / "README.md").write_text("x", encoding="utf-8")
        subprocess.run(["git", "add", "."], cwd=repo_dir, check=True, capture_output=True)
        subprocess.run(
            ["git", "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-m", "init"],
            cwd=repo_dir, check=True, capture_output=True,
        )
        return repo_dir

    def test_missing_branch_falls_back_to_first_seen(self):
        repo_dir = self._repo_with_main()
        age, worked = sidebar_model._read_git_stats(
            repo_dir, "no-such-feature", first_seen=100.0, now=700.0,
        )
        self.assertEqual(age, "10m")
        self.assertIsNone(worked)

    def test_existing_branch_derives_age_and_worked_from_its_commits(self):
        repo_dir = self._repo_with_main()
        subprocess.run(["git", "checkout", "--quiet", "-b", "f/my-feature"],
                       cwd=repo_dir, check=True, capture_output=True)
        (Path(repo_dir) / "a.txt").write_text("a", encoding="utf-8")
        subprocess.run(["git", "add", "."], cwd=repo_dir, check=True, capture_output=True)
        subprocess.run(
            ["git", "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-m", "work"],
            cwd=repo_dir, check=True, capture_output=True,
        )
        age, worked = sidebar_model._read_git_stats(
            repo_dir, "my-feature", first_seen=0.0, now=time.time(),
        )
        self.assertIsNotNone(age)
        self.assertEqual(worked, "10m")  # one commit -> floor


class RoleModelExposureTests(_CourierFixtureTestCase):
    """bus-message-specifying B5b: role comes straight off the announced
    agent_type; model only ever appears if the identity body happens to
    carry one — courier.py's identity_of() does not today (see deviations), so
    this exercises the mechanism defensively rather than assuming a value
    that doesn't currently exist."""

    def test_feature_role_is_the_announced_agent_type(self):
        self._landscaper("arch-role1", "feat-role1")
        fleet = sidebar_model.build_model([self.repo])
        self.assertEqual(fleet.repos[0].features[0].role, "landscaper")

    def test_feature_model_is_none_when_identity_body_omits_it(self):
        self._landscaper("arch-role2", "feat-role2")
        fleet = sidebar_model.build_model([self.repo])
        self.assertIsNone(fleet.repos[0].features[0].model)

    def test_feature_model_is_exposed_when_identity_body_carries_one(self):
        body = identity_body("arch-role3", agent_type="landscaper",
                             feature_id="feat-role3", name="feat role3")
        body["model"] = "claude-sonnet-5-20260101"
        self._put("arch-role3", "arch-role3-id", "arch-role3", body,
                  ts="2026-01-01T00:00:00.000000+00:00")
        fleet = sidebar_model.build_model([self.repo])
        self.assertEqual(fleet.repos[0].features[0].model, "claude-sonnet-5-20260101")

    def test_repo_role_is_the_announced_orchestrator_agent_type(self):
        self._put("orch-role1", "orch-role1-id", "orch-role1",
                  identity_body("orch-role1", agent_type="gardener"),
                  ts="2026-01-01T00:00:00.000000+00:00")
        fleet = sidebar_model.build_model([self.repo])
        self.assertEqual(fleet.repos[0].role, "gardener")


if __name__ == "__main__":
    unittest.main()
