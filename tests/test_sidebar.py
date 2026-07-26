"""Unit tests for tools/sidebar.py — the consolidated fleet sidebar (bus-
finishing): tools/sidebar_model.py and tools/sidebar_v3.py are both retired
and folded into tools/sidebar.py, which reads
`$XDG_RUNTIME_DIR/orchard/projects/<repo>.<project>/<sessionid>.<ts>.json`
directly (see that module's own docstring). This file covers:

  - build_model() against fixture event files (status derivation,
    subagent begin/end, identity-derived repo/feature/role/name, the
    active-window filter) — written either straight to disk (matching the
    on-disk shape orchard_topic.py's write_message()/build_envelope()
    produce) or, for one end-to-end smoke test, via a real
    `orchard_topic.py post` subprocess.
  - flatten()/render_lines()/the `--dump` CLI on the resulting Fleet.
  - the pure presentation/colour/layout helpers that have no model
    dependency at all.

Retired along with sidebar_model.py and NOT re-tested here (no source in
the new event grammar — see sidebar.py's module docstring): courier rows,
open-question badges, phase ticks, tokens/dollars, age/worked.

Runs under both `python3 -m unittest discover` and `pytest`; stdlib only.
"""
import curses
import itertools
import json
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from datetime import datetime, timezone
from unittest import mock
from pathlib import Path

_TOOLS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools",
)
if _TOOLS_DIR not in sys.path:
    sys.path.insert(0, _TOOLS_DIR)

import sidebar  # noqa: E402

from support import make_repo  # noqa: E402

_SIDEBAR_PY = os.path.join(_TOOLS_DIR, "sidebar.py")
_ORCHARD_TOPIC_PY = os.path.join(_TOOLS_DIR, "orchard_topic.py")


# --------------------------------------------------------------------------
# Fixture helpers — write raw event files directly into a projects root,
# matching the shape orchard_topic.py's build_envelope()/write_message()
# produce (from/subject/body/identity/status), without needing a real git
# repo or session for every scenario.
# --------------------------------------------------------------------------

_counter = itertools.count()


def _write_event(projects_root, slug, sid, subject, *,
                  identity=None, status=None, body=None, mtime=None):
    """One event file under `projects_root`/`slug`/. `mtime`, when given,
    overrides the FILE's own mtime (build_model()'s "latest of each kind
    wins" folding reads `f.stat().st_mtime`, not any embedded timestamp —
    see sidebar.py's `_fold_sessions`) — this is what a session's staleness
    check (`_status_for`, retention ruling 2026-07-25 revision) reads, via
    each record's own `_seen_ts`. The project dir's own mtime is always
    bumped to "now" afterwards, mirroring orchard_topic.py's own
    write_message()/_bump_chain(); it no longer gates visibility (nothing
    is ever excluded from build_model() any more — staleness is a colour,
    not a removal), only per-session recency does."""
    project_dir = Path(projects_root) / slug
    project_dir.mkdir(parents=True, exist_ok=True)
    envelope = {"from": f":session:{sid}", "subject": subject}
    if body is not None:
        envelope["body"] = body
    if identity is not None:
        envelope["identity"] = identity
    if status is not None:
        envelope["status"] = status
    path = project_dir / f"{sid}.{next(_counter):08d}.json"
    path.write_text(json.dumps(envelope), encoding="utf-8")
    if mtime is not None:
        os.utime(path, (mtime, mtime))
    os.utime(project_dir, None)
    return path


def _iso(ts) -> str:
    return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _write_marker(projects_root, slug, feature_id, *, name=None, area=None,
                   state=None, updated=None, archived=False, extra=None):
    """One `<feature-id>.marker` file under `projects_root`/`slug`/ (or its
    `_archived/` subdirectory when `archived`) — the schema courier.py's
    transport actually writes (operator ruling, 2026-07-26): a `tasks`
    list, each entry carrying its own `feature`/`name`/`area`/`state`/
    `updated`, nothing agent-shaped, no `sessions` map. `name`/`area`/
    `state`/`updated` here populate that single task entry (courier.py
    scopes exactly one task per feature today). `extra` merges in
    additional top-level keys a test wants present on the JSON — e.g. a
    legacy `sessions` block, to prove the reader ignores it rather than
    assuming it's absent."""
    project_dir = Path(projects_root) / slug / ("_archived" if archived else "")
    project_dir.mkdir(parents=True, exist_ok=True)
    task_updated = updated or _now_iso()
    marker = {
        "schema": 1, "project": slug, "feature": feature_id,
        "tasks": [{"feature": feature_id, "name": name, "area": area,
                    "state": state, "updated": task_updated}],
        "updated": task_updated,
    }
    if extra:
        marker.update(extra)
    path = project_dir / f"{feature_id}.marker"
    path.write_text(json.dumps(marker), encoding="utf-8")
    return path


class _FixtureTestCase(unittest.TestCase):
    """One private projects-root temp dir per test — passed straight to
    build_model(root=...), bypassing $XDG_RUNTIME_DIR entirely."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.projects_root = Path(self._tmp.name) / "projects"
        self.projects_root.mkdir(parents=True)

    def _event(self, slug, sid, subject, **kw):
        return _write_event(self.projects_root, slug, sid, subject, **kw)

    def _model(self, now=None) -> sidebar.Fleet:
        return sidebar.build_model(self.projects_root, now=now)

    def _repo(self, slug="own.repo", now=None) -> sidebar.Repo:
        fleet = self._model(now=now)
        self.assertEqual(len(fleet.repos), 1)
        return fleet.repos[0]

    def _landscaper(self, slug, sid, feature, name=None, mtime=None):
        """Announce a landscaper session — the minimum needed for a Feature
        row to exist."""
        self._event(slug, sid, "orchard:agent:lifecycle:starting",
                     identity={"agent": "landscaper", "feature": feature,
                               **({"name": name} if name else {})},
                     mtime=mtime)


# --------------------------------------------------------------------------
# Status derivation — working/done/failed/idle, from lifecycle + outcome.
# --------------------------------------------------------------------------

class StatusDerivationTests(_FixtureTestCase):
    def test_lifecycle_starting_is_working(self):
        self._landscaper("own.repo", "s1", "feat-a")
        feature = self._repo().features[0]
        self.assertEqual(feature.status, "working")

    def test_lifecycle_stopping_is_working(self):
        self._event("own.repo", "s1", "orchard:agent:lifecycle:stopping",
                     identity={"agent": "landscaper", "feature": "feat-a"})
        feature = self._repo().features[0]
        self.assertEqual(feature.status, "working")

    def test_lifecycle_stopped_alone_is_idle(self):
        # "stopped" is deliberately not in the working-state tuple (only
        # starting/started/stopping are) -- with no outcome/task_outcome
        # yet posted, a stopped-but-not-yet-outcome session reads as idle,
        # not working and not done.
        self._event("own.repo", "s1", "orchard:agent:lifecycle:stopped",
                     identity={"agent": "landscaper", "feature": "feat-a"})
        feature = self._repo().features[0]
        self.assertEqual(feature.status, "idle")

    def test_no_signal_is_idle(self):
        self._landscaper("own.repo", "s1", "feat-a", mtime=1)
        # identity-only, no lifecycle/outcome distinguishes idle from
        # working -- but _landscaper already posts a "starting" lifecycle,
        # so post a fresh identity-only announce with no lifecycle subject.
        self._event("own.repo", "s2", "orchard:agent:status",
                     identity={"agent": "landscaper", "feature": "feat-b"},
                     body="idle")
        features = {f.name: f for f in self._repo().features}
        self.assertEqual(features["feat-b"].status, "idle")

    def test_outcome_success_is_done(self):
        self._event("own.repo", "s1", "orchard:agent:outcome:success",
                     identity={"agent": "landscaper", "feature": "feat-a"})
        feature = self._repo().features[0]
        self.assertEqual(feature.status, "done")

    def test_outcome_fail_is_failed(self):
        self._event("own.repo", "s1", "orchard:agent:outcome:fail",
                     identity={"agent": "landscaper", "feature": "feat-a"})
        feature = self._repo().features[0]
        self.assertEqual(feature.status, "failed")

    def test_task_outcome_completed_is_done(self):
        self._event("own.repo", "s1", "orchard:task:outcome:completed",
                     identity={"agent": "landscaper", "feature": "feat-a"})
        feature = self._repo().features[0]
        self.assertEqual(feature.status, "done")

    def test_task_outcome_failed_is_failed(self):
        self._event("own.repo", "s1", "orchard:task:outcome:failed",
                     identity={"agent": "landscaper", "feature": "feat-a"})
        feature = self._repo().features[0]
        self.assertEqual(feature.status, "failed")

    def test_done_and_failed_never_share_encoding(self):
        self._event("own.repo", "s-done", "orchard:agent:outcome:success",
                     identity={"agent": "landscaper", "feature": "feat-done"})
        self._event("own.repo", "s-fail", "orchard:agent:outcome:fail",
                     identity={"agent": "landscaper", "feature": "feat-fail"})
        features = {f.name: f for f in self._repo().features}
        self.assertEqual(features["feat-done"].status, "done")
        self.assertEqual(features["feat-fail"].status, "failed")
        self.assertNotEqual(features["feat-done"].status, features["feat-fail"].status)

    def test_status_progresses_through_lifecycle_then_outcome(self):
        # a single session's status transitions working -> done as later
        # (by file mtime) events land -- each build_model() call is a fresh
        # snapshot, matching how the real curses loop re-derives on watch.
        # Timestamps are recent-but-ordered (not tiny absolute epoch ints)
        # so the first event stays inside ACTIVE_WINDOW_SECONDS and reads
        # "working" rather than "stale" (see StalenessTests for the
        # stale-vs-working boundary itself).
        import time
        now = time.time()
        self._event("own.repo", "s1", "orchard:agent:lifecycle:starting",
                     identity={"agent": "landscaper", "feature": "feat-a"}, mtime=now - 100)
        self.assertEqual(self._repo().features[0].status, "working")

        self._event("own.repo", "s1", "orchard:agent:outcome:success",
                     identity={"agent": "landscaper", "feature": "feat-a"}, mtime=now - 50)
        self.assertEqual(self._repo().features[0].status, "done")

    def test_activity_is_the_latest_status_body(self):
        self._event("own.repo", "s1", "orchard:agent:lifecycle:starting",
                     identity={"agent": "landscaper", "feature": "feat-a"}, mtime=1)
        self._event("own.repo", "s1", "orchard:agent:status",
                     identity={"agent": "landscaper", "feature": "feat-a"},
                     body="reading files", mtime=2)
        feature = self._repo().features[0]
        self.assertEqual(feature.activity, "reading files")
        self.assertEqual(feature.status_word, "reading files")


# --------------------------------------------------------------------------
# Subagent begin/end (orchard:agent:delegation:begin|end — EXACT subject,
# no appended subagent id: the subagent rides the body instead, operator
# ruling that the orchard subject list is closed and variable data never
# belongs in the subject).
# --------------------------------------------------------------------------

class SubagentDelegationTests(_FixtureTestCase):
    def test_begin_without_end_is_present(self):
        self._landscaper("own.repo", "s1", "feat-a", mtime=1)
        self._event("own.repo", "s1", "orchard:agent:delegation:begin",
                     identity={"agent": "landscaper", "feature": "feat-a"},
                     body={"subagent": "sub-a"}, mtime=2)
        feature = self._repo().features[0]
        self.assertEqual([s.label for s in feature.subagents], ["sub-a"])

    def test_begin_then_end_is_absent(self):
        self._landscaper("own.repo", "s1", "feat-a", mtime=1)
        self._event("own.repo", "s1", "orchard:agent:delegation:begin",
                     identity={"agent": "landscaper", "feature": "feat-a"},
                     body={"subagent": "sub-a"}, mtime=2)
        self._event("own.repo", "s1", "orchard:agent:delegation:end",
                     identity={"agent": "landscaper", "feature": "feat-a"},
                     body={"subagent": "sub-a"}, mtime=3)
        feature = self._repo().features[0]
        self.assertEqual(feature.subagents, [])

    def test_schedule_increments_queued_without_a_subagent_row(self):
        """`schedule` (restored per operator ruling, 2026-07-25) sets
        subagents_queued but does NOT add a Subagent row — only `begin`
        promotes a subagent to an active, rendered row (EXACT subject, no
        appended id: the subagent id rides the body)."""
        self._landscaper("own.repo", "s1", "feat-a", mtime=1)
        self._event("own.repo", "s1", "orchard:agent:delegation:schedule",
                     identity={"agent": "landscaper", "feature": "feat-a"},
                     body={"subagent": "sub-a"}, mtime=2)
        feature = self._repo().features[0]
        self.assertEqual(feature.subagents, [])
        self.assertEqual(feature.subagents_queued, 1)
        self.assertEqual(feature.subagents_running, 0)

    def test_schedule_then_begin_moves_from_queued_to_running(self):
        self._landscaper("own.repo", "s1", "feat-a", mtime=1)
        self._event("own.repo", "s1", "orchard:agent:delegation:schedule",
                     identity={"agent": "landscaper", "feature": "feat-a"},
                     body={"subagent": "sub-a"}, mtime=2)
        self._event("own.repo", "s1", "orchard:agent:delegation:begin",
                     identity={"agent": "landscaper", "feature": "feat-a"},
                     body={"subagent": "sub-a"}, mtime=3)
        feature = self._repo().features[0]
        self.assertEqual([s.label for s in feature.subagents], ["sub-a"])
        self.assertEqual(feature.subagents_queued, 0)
        self.assertEqual(feature.subagents_running, 1)

    def test_stray_schedule_with_appended_subagent_id_is_not_matched(self):
        """The old family/prefix shape (`delegation:schedule:sub-a`, id
        appended to the subject) is not the restored subject — EXACT
        comparison only, so a stray event in that old shape still does not
        contribute to the queued count."""
        self._landscaper("own.repo", "s1", "feat-a", mtime=1)
        self._event("own.repo", "s1", "orchard:agent:delegation:schedule:sub-a",
                     identity={"agent": "landscaper", "feature": "feat-a"}, mtime=2)
        feature = self._repo().features[0]
        self.assertEqual(feature.subagents, [])
        self.assertEqual(feature.subagents_queued, 0)
        self.assertEqual(feature.subagents_running, 0)

    def test_multiple_active_subagents_sorted_by_label(self):
        self._landscaper("own.repo", "s1", "feat-a", mtime=1)
        self._event("own.repo", "s1", "orchard:agent:delegation:begin",
                     identity={"agent": "landscaper", "feature": "feat-a"},
                     body={"subagent": "sub-c"}, mtime=2)
        self._event("own.repo", "s1", "orchard:agent:delegation:begin",
                     identity={"agent": "landscaper", "feature": "feat-a"},
                     body={"subagent": "sub-a"}, mtime=3)
        self._event("own.repo", "s1", "orchard:agent:delegation:begin",
                     identity={"agent": "landscaper", "feature": "feat-a"},
                     body={"subagent": "sub-b"}, mtime=4)
        feature = self._repo().features[0]
        self.assertEqual([s.label for s in feature.subagents], ["sub-a", "sub-b", "sub-c"])


# --------------------------------------------------------------------------
# Identity-derived label/role/model
# --------------------------------------------------------------------------

class IdentityDerivedTests(_FixtureTestCase):
    def test_feature_label_prefers_announced_name_over_feature(self):
        self._event("own.repo", "s1", "orchard:agent:lifecycle:starting",
                     identity={"agent": "landscaper", "feature": "feat-a", "name": "Feature A"})
        feature = self._repo().features[0]
        self.assertEqual(feature.name, "Feature A")

    def test_feature_label_falls_back_to_feature_id_without_a_name(self):
        self._event("own.repo", "s1", "orchard:agent:lifecycle:starting",
                     identity={"agent": "landscaper", "feature": "feat-a"})
        feature = self._repo().features[0]
        self.assertEqual(feature.name, "feat-a")

    def test_feature_label_falls_back_to_session_id_without_name_or_feature(self):
        self._event("own.repo", "not-a-uuid-session", "orchard:agent:lifecycle:starting",
                     identity={"agent": "landscaper"})
        feature = self._repo().features[0]
        self.assertEqual(feature.name, "not-a-uuid-session")

    def test_bare_uuid_session_with_no_name_or_feature_is_hidden(self):
        self._event("own.repo", "3fa85f64-5717-4562-b3fc-2c963f66afa6",
                     "orchard:agent:lifecycle:starting", identity={"agent": "landscaper"})
        self.assertEqual(self._repo().features, [])

    def test_bare_uuid_session_with_an_announced_name_is_shown(self):
        self._event("own.repo", "3fa85f64-5717-4562-b3fc-2c963f66afa6",
                     "orchard:agent:lifecycle:starting",
                     identity={"agent": "landscaper", "name": "named session"})
        feature = self._repo().features[0]
        self.assertEqual(feature.name, "named session")

    def test_feature_role_is_the_announced_agent(self):
        self._event("own.repo", "s1", "orchard:agent:lifecycle:starting",
                     identity={"agent": "landscaper", "feature": "feat-a"})
        feature = self._repo().features[0]
        self.assertEqual(feature.role, "landscaper")

    def test_feature_model_is_none_when_status_omits_it(self):
        self._event("own.repo", "s1", "orchard:agent:lifecycle:starting",
                     identity={"agent": "landscaper", "feature": "feat-a"})
        feature = self._repo().features[0]
        self.assertIsNone(feature.model)

    def test_feature_model_is_exposed_when_status_carries_one(self):
        self._event("own.repo", "s1", "orchard:agent:lifecycle:starting",
                     identity={"agent": "landscaper", "feature": "feat-a"},
                     status={"model": "claude-sonnet-5-20260101"})
        feature = self._repo().features[0]
        self.assertEqual(feature.model, "claude-sonnet-5-20260101")

    def test_repo_role_is_the_announced_gardener(self):
        self._event("own.repo", "g1", "orchard:agent:lifecycle:starting",
                     identity={"agent": "gardener"})
        self.assertEqual(self._repo().role, "gardener")

    def test_repo_display_name_strips_owner_prefix(self):
        self._event("someowner.somerepo", "g1", "orchard:agent:lifecycle:starting",
                     identity={"agent": "gardener"})
        fleet = self._model()
        self.assertEqual(fleet.repos[0].name, "somerepo")

    def test_repo_display_name_without_owner_dot_is_shown_as_is(self):
        self._event("bare-slug", "g1", "orchard:agent:lifecycle:starting",
                     identity={"agent": "gardener"})
        fleet = self._model()
        self.assertEqual(fleet.repos[0].name, "bare-slug")


# --------------------------------------------------------------------------
# Repo assembly — gardener vs. landscaper, has_session, cross-feature.
# --------------------------------------------------------------------------

class RepoAssemblyTests(_FixtureTestCase):
    def test_gardener_session_does_not_become_a_feature_row(self):
        self._event("own.repo", "g1", "orchard:agent:lifecycle:starting",
                     identity={"agent": "gardener"})
        repo = self._repo()
        self.assertEqual(repo.features, [])
        self.assertTrue(repo.has_session)

    def test_multiple_landscapers_become_multiple_features(self):
        self._landscaper("own.repo", "s1", "feat-a")
        self._landscaper("own.repo", "s2", "feat-b")
        repo = self._repo()
        self.assertEqual(sorted(f.name for f in repo.features), ["feat-a", "feat-b"])

    def test_two_parents_each_show_their_own_subagents(self):
        self._landscaper("own.repo", "s1", "feat-a", mtime=1)
        self._event("own.repo", "s1", "orchard:agent:delegation:begin",
                     identity={"agent": "landscaper", "feature": "feat-a"},
                     body={"subagent": "sub-1"}, mtime=2)
        self._landscaper("own.repo", "s2", "feat-b", mtime=1)
        self._event("own.repo", "s2", "orchard:agent:delegation:begin",
                     identity={"agent": "landscaper", "feature": "feat-b"},
                     body={"subagent": "sub-2"}, mtime=2)

        features = {f.name: f for f in self._repo().features}
        self.assertEqual([s.label for s in features["feat-a"].subagents], ["sub-1"])
        self.assertEqual([s.label for s in features["feat-b"].subagents], ["sub-2"])

    def test_has_session_false_when_project_dir_has_no_recognisable_session(self):
        project_dir = self.projects_root / "own.repo"
        project_dir.mkdir(parents=True)
        (project_dir / "s1.marker").touch()  # heartbeat only, no event file
        fleet = self._model()
        self.assertEqual(len(fleet.repos), 1)
        self.assertFalse(fleet.repos[0].has_session)

    def test_has_session_true_with_gardener_only(self):
        self._event("own.repo", "g1", "orchard:agent:lifecycle:starting",
                     identity={"agent": "gardener"})
        self.assertTrue(self._repo().has_session)

    def test_has_session_true_with_feature_only(self):
        self._landscaper("own.repo", "s1", "feat-a")
        self.assertTrue(self._repo().has_session)


# --------------------------------------------------------------------------
# Staleness — the ~1h ACTIVE_WINDOW is purely a colour signal now (retention
# ruling, 2026-07-25, revised same day): nothing is ever dropped from the
# model for being stale. A session with no event inside the window and no
# terminal outcome reads "stale" (gray) but stays in the fleet; a terminal
# outcome (done/failed) always wins over staleness and is a permanent
# green/red one-liner. A row leaves the sidebar only when the process
# restarts (the tmpfs projects tree clears with it) — not modelled here,
# since build_model() has no notion of "restart", only of what is currently
# on disk.
# --------------------------------------------------------------------------

class StalenessTests(_FixtureTestCase):
    def test_no_recent_event_and_no_outcome_reads_stale(self):
        self._event("own.repo", "s1", "orchard:agent:lifecycle:starting",
                     identity={"agent": "landscaper", "feature": "feat-a"},
                     mtime=self._stale_ts())
        feature = self._repo().features[0]
        self.assertEqual(feature.status, "stale")

    def test_stale_session_is_never_dropped_from_the_model(self):
        self._event("own.repo", "s1", "orchard:agent:lifecycle:starting",
                     identity={"agent": "landscaper", "feature": "feat-a"},
                     mtime=self._stale_ts())
        fleet = self._model()
        self.assertEqual(len(fleet.repos), 1)
        self.assertEqual([f.name for f in fleet.repos[0].features], ["feat-a"])

    def test_recent_event_is_working_not_stale(self):
        self._landscaper("own.repo", "s1", "feat-a")
        feature = self._repo().features[0]
        self.assertEqual(feature.status, "working")

    def test_success_outcome_overrides_staleness_and_stays_done(self):
        self._event("own.repo", "s1", "orchard:agent:outcome:success",
                     identity={"agent": "landscaper", "feature": "feat-a"},
                     mtime=self._stale_ts())
        feature = self._repo().features[0]
        self.assertEqual(feature.status, "done")

    def test_fail_outcome_overrides_staleness_and_stays_failed(self):
        self._event("own.repo", "s1", "orchard:agent:outcome:fail",
                     identity={"agent": "landscaper", "feature": "feat-a"},
                     mtime=self._stale_ts())
        feature = self._repo().features[0]
        self.assertEqual(feature.status, "failed")

    def test_finished_and_stale_features_coexist_in_the_same_repo(self):
        self._event("own.repo", "s-old", "orchard:agent:outcome:success",
                     identity={"agent": "landscaper", "feature": "feat-done"},
                     mtime=self._stale_ts())
        self._event("own.repo", "s-stale", "orchard:agent:lifecycle:starting",
                     identity={"agent": "landscaper", "feature": "feat-stale"},
                     mtime=self._stale_ts())
        self._landscaper("own.repo", "s-fresh", "feat-fresh")
        features = {f.name: f for f in self._repo().features}
        self.assertEqual(set(features), {"feat-done", "feat-stale", "feat-fresh"})
        self.assertEqual(features["feat-done"].status, "done")
        self.assertEqual(features["feat-stale"].status, "stale")
        self.assertEqual(features["feat-fresh"].status, "working")

    @staticmethod
    def _stale_ts():
        import time
        return time.time() - sidebar.ACTIVE_WINDOW_SECONDS - 60


# --------------------------------------------------------------------------
# Feature-node markers (frozen schema, `<feature-id>.marker`) — the
# structural tree source for a TASK row: any identity earns a live row (not
# just landscaper), and a task with no live agent at all still renders as
# a single row carrying its marker's persisted name/state, nothing beneath
# it (operator ruling, 2026-07-26: "the task is the one that doesn't
# disappear"). See sidebar.py's `_iter_feature_markers`, `_marker_only_rec`,
# `_assemble_repo`.
# --------------------------------------------------------------------------

class MarkerModelTests(_FixtureTestCase):
    def test_non_landscaper_identity_with_live_events_renders_a_row(self):
        self._event("own.repo", "s1", "orchard:agent:lifecycle:starting",
                     identity={"agent": "architect", "feature": "feat-a"})
        feature = self._repo().features[0]
        self.assertEqual(feature.name, "feat-a")
        self.assertEqual(feature.role, "architect")
        self.assertEqual(feature.status, "working")

    def test_marker_only_task_renders_one_row_with_terminal_state_and_nothing_else(self):
        # a task with a marker but zero live events: exactly one row, its
        # terminal state, no agent subscript, no subagent rows.
        _write_marker(self.projects_root, "own.repo", "feat-a", name="Feature A", state="done")
        features = self._repo().features
        self.assertEqual(len(features), 1)
        feature = features[0]
        self.assertEqual(feature.name, "Feature A")
        self.assertEqual(feature.status, "done")
        self.assertIsNone(feature.role)
        self.assertIsNone(feature.model)
        self.assertEqual(feature.subagents, [])

    def test_marker_only_task_falls_back_to_the_feature_id_without_a_name(self):
        _write_marker(self.projects_root, "own.repo", "feat-a", state="failed")
        feature = self._repo().features[0]
        self.assertEqual(feature.name, "feat-a")
        self.assertEqual(feature.status, "failed")

    def test_marker_only_task_with_recent_updated_and_no_terminal_state_reads_idle(self):
        _write_marker(self.projects_root, "own.repo", "feat-a")
        feature = self._repo().features[0]
        self.assertEqual(feature.status, "idle")

    def test_marker_only_task_with_stale_updated_and_no_terminal_state_reads_stale(self):
        stale_iso = _iso(StalenessTests._stale_ts())
        _write_marker(self.projects_root, "own.repo", "feat-a", updated=stale_iso)
        feature = self._repo().features[0]
        self.assertEqual(feature.status, "stale")

    def test_marker_only_task_with_working_state_inside_the_window_renders_working(self):
        # bug fix, 2026-07-26: a marker-only task declaring "working" must
        # be reachable to "working" once its own event telemetry has aged
        # out — this was never true before (see `_marker_task_rec`).
        _write_marker(self.projects_root, "own.repo", "feat-a", state="working")
        feature = self._repo().features[0]
        self.assertEqual(feature.status, "working")

    def test_marker_only_task_with_working_state_outside_the_window_still_reads_stale(self):
        # Decision-094: staleness is a colour, not a removal, and it is not
        # bypassed by a marker's own claim of "working" — a task not heard
        # from within ACTIVE_WINDOW_SECONDS reads stale regardless.
        stale_iso = _iso(StalenessTests._stale_ts())
        _write_marker(self.projects_root, "own.repo", "feat-a", state="working",
                       updated=stale_iso)
        feature = self._repo().features[0]
        self.assertEqual(feature.status, "stale")

    def test_marker_only_task_with_done_state_and_stale_updated_still_reads_done(self):
        # done/failed are terminal and are never demoted by staleness, no
        # matter how old the marker's own `updated` is.
        stale_iso = _iso(StalenessTests._stale_ts())
        _write_marker(self.projects_root, "own.repo", "feat-a", state="done",
                       updated=stale_iso)
        feature = self._repo().features[0]
        self.assertEqual(feature.status, "done")

    def test_marker_only_task_never_restores_agent_identity_even_from_a_legacy_sessions_block(self):
        # corrected contract: role/model are live-only. A marker carrying a
        # stale legacy `sessions` block (tolerated, per the transport's own
        # migration) must never be read for identity.
        _write_marker(self.projects_root, "own.repo", "feat-a", state="done",
                       extra={"sessions": {"s1": {"agent": "architect", "state": "done"}}})
        feature = self._repo().features[0]
        self.assertIsNone(feature.role)
        self.assertIsNone(feature.model)

    def test_task_row_survives_after_its_events_are_archived(self):
        self._event("own.repo", "s1", "orchard:agent:outcome:success",
                     identity={"agent": "landscaper", "feature": "feat-a"})
        _write_marker(self.projects_root, "own.repo", "feat-a", state="done")
        # Simulate the archiver removing the 120-minute-old event JSONs —
        # the marker alone must keep the row alive.
        for f in (self.projects_root / "own.repo").glob("*.json"):
            f.unlink()
        feature = self._repo().features[0]
        self.assertEqual(feature.status, "done")

    def test_live_agent_subscript_and_subagents_vanish_once_its_events_are_gone(self):
        # mtimes deliberately keep the identity-carrying event as the
        # latest snapshot -- delegation:begin carries no `status` block of
        # its own, so if it were processed as the latest snapshot instead
        # it would blank out the already-known model (a pre-existing,
        # unrelated quirk of the file-order-independent "latest wins"
        # fold, sidestepped here rather than fixed, out of this step's
        # scope).
        self._event("own.repo", "s1", "orchard:agent:delegation:begin",
                     identity={"agent": "landscaper", "feature": "feat-a"},
                     body={"subagent": "sub-a"}, mtime=1)
        self._event("own.repo", "s1", "orchard:agent:lifecycle:starting",
                     identity={"agent": "landscaper", "feature": "feat-a"},
                     status={"model": "claude-sonnet-5"}, mtime=2)
        _write_marker(self.projects_root, "own.repo", "feat-a", name="Feature A", state="done")

        feature = self._repo().features[0]
        self.assertEqual(feature.role, "landscaper")
        self.assertEqual(feature.model, "claude-sonnet-5")
        self.assertEqual([s.label for s in feature.subagents], ["sub-a"])

        for f in (self.projects_root / "own.repo").glob("*.json"):
            f.unlink()
        feature = self._repo().features[0]
        self.assertIsNone(feature.role)
        self.assertIsNone(feature.model)
        self.assertEqual(feature.subagents, [])
        self.assertEqual(feature.status, "done")

    def test_archived_marker_subdirectory_is_ignored(self):
        _write_marker(self.projects_root, "own.repo", "feat-old", state="done", archived=True)
        fleet = self._model()
        self.assertEqual(fleet.repos[0].features, [])

    def test_legacy_label_task_and_sessions_block_never_resurrect_a_subagent_row(self):
        # captured live regression: a marker still carrying a rejected
        # earlier shape (a `sessions` identity cache, and a `{"label": ...}`
        # tasks[] entry with no `feature` — a subagent delegation label)
        # alongside one genuine current task. Only the genuine task may
        # ever render; the label entry must not be name-substituted from
        # the marker's own feature id and drawn as a second, done row.
        _write_marker(
            self.projects_root, "own.repo", "sidebar-empty-rows",
            extra={
                "sessions": {"s1": {"agent": "architect", "state": "done"}},
                "tasks": [
                    {"label": "verify-task-persist", "state": "done",
                     "updated": _now_iso()},
                    {"feature": "sidebar-empty-rows",
                     "name": "Sidebar empty rows: head", "area": None,
                     "state": "working", "updated": _now_iso()},
                ],
            },
        )
        features = self._repo().features
        self.assertEqual(len(features), 1)
        self.assertEqual(features[0].name, "Sidebar empty rows: head")
        # a fresh `updated` with a "working" state now reads "working" (bug
        # fix, 2026-07-26 — see `_marker_task_rec`/`_MARKER_STATE_LIFECYCLE`);
        # what stays fixed by this test is that the rejected `label`-only
        # sibling never contributes a second row or borrows this row's name.
        self.assertEqual(features[0].status, "working")

    def test_live_session_for_the_same_feature_wins_over_its_marker(self):
        self._landscaper("own.repo", "s1", "feat-a")
        _write_marker(self.projects_root, "own.repo", "feat-a", name="stale name", state="done")
        features = self._repo().features
        self.assertEqual(len(features), 1)
        self.assertEqual(features[0].status, "working")
        self.assertEqual(features[0].role, "landscaper")


# --------------------------------------------------------------------------
# Subagent rows are live-only (operator ruling, 2026-07-26): a delegation's
# row disappears the instant its own events are gone, whatever the owning
# task's marker says — the marker holds nothing subagent-shaped any more.
# --------------------------------------------------------------------------

class MarkerTaskPersistenceTests(_FixtureTestCase):
    def test_subagent_row_disappears_once_its_events_are_archived(self):
        self._landscaper("own.repo", "s1", "feat-a", mtime=1)
        self._event("own.repo", "s1", "orchard:agent:delegation:begin",
                     identity={"agent": "landscaper", "feature": "feat-a"},
                     body={"subagent": "sub-a"}, mtime=2)
        _write_marker(self.projects_root, "own.repo", "feat-a", state="working")
        for f in (self.projects_root / "own.repo").glob("*.json"):
            f.unlink()
        feature = self._repo().features[0]
        self.assertEqual(feature.subagents, [])

    def test_marker_is_never_consulted_for_subagent_rows_even_while_the_agent_is_live(self):
        self._landscaper("own.repo", "s1", "feat-a", mtime=1)
        _write_marker(self.projects_root, "own.repo", "feat-a", name="Feature A", state="working")
        feature = self._repo().features[0]
        self.assertEqual(feature.subagents, [])


# --------------------------------------------------------------------------
# End-to-end smoke test: post through the REAL orchard_topic.py writer (a
# real git repo + session id + XDG_RUNTIME_DIR), then read it back with
# build_model() — confirms sidebar.py's reader stays compatible with the
# real writer's on-disk shape, not just this file's own fixture helper.
# --------------------------------------------------------------------------

class OrchardTopicPostIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.repo = make_repo(self._tmp.name)
        self.runtime_dir = Path(self._tmp.name) / "run"
        self.runtime_dir.mkdir()

    def _post(self, *args):
        env = dict(os.environ)
        env["CLAUDE_CODE_SESSION_ID"] = "smoke-session"
        env["CLAUDE_CODE_AGENT"] = "gardener"
        env["XDG_RUNTIME_DIR"] = str(self.runtime_dir)
        return subprocess.run(
            [sys.executable, _ORCHARD_TOPIC_PY, "post", *args],
            cwd=self.repo, capture_output=True, text=True, env=env,
        )

    def test_real_lifecycle_post_is_readable_by_build_model(self):
        proc = self._post("lifecycle", "started")
        self.assertEqual(proc.returncode, 0, proc.stderr)

        delivered = Path(proc.stdout.strip())
        projects_root = delivered.parent.parent
        fleet = sidebar.build_model(projects_root)

        self.assertEqual(len(fleet.repos), 1)
        repo = fleet.repos[0]
        self.assertEqual(repo.role, "gardener")
        self.assertEqual(repo.status, "working")
        self.assertTrue(repo.has_session)


# --------------------------------------------------------------------------
# CLI --dump — real subprocess, headless, exercises build_model() +
# render_lines() together the way the operator's terminal does.
# --------------------------------------------------------------------------

class DumpCLITests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.runtime_dir = Path(self._tmp.name)
        self.projects_root = self.runtime_dir / "orchard" / "projects"
        self.projects_root.mkdir(parents=True)

    def _dump(self):
        env = dict(os.environ)
        env["XDG_RUNTIME_DIR"] = str(self.runtime_dir)
        proc = subprocess.run(
            [sys.executable, _SIDEBAR_PY, "--dump"],
            capture_output=True, text=True, env=env,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        return proc.stdout.splitlines()

    def test_dump_with_no_projects_shows_no_activity(self):
        lines = self._dump()
        self.assertEqual(lines, [sidebar.NO_ACTIVITY_TEXT])

    def test_dump_renders_repo_header_and_working_feature(self):
        _write_event(self.projects_root, "own.repo", "s1",
                      "orchard:agent:lifecycle:starting",
                      identity={"agent": "landscaper", "feature": "feat-a",
                                "name": "feat a"})
        lines = self._dump()
        # "own.repo" is an <owner>.<repo> slug -- _repo_display_name() shows
        # only the bare "repo" part.
        self.assertTrue(any(l.strip() == "repo" for l in lines))
        feature_line = next(l for l in lines if "feat a" in l)
        self.assertIn(sidebar.STATUS_EMOJI["working"], feature_line)

    def test_dump_renders_subagent_row_under_its_feature(self):
        _write_event(self.projects_root, "own.repo", "s1",
                      "orchard:agent:lifecycle:starting",
                      identity={"agent": "landscaper", "feature": "feat-a"}, mtime=1)
        _write_event(self.projects_root, "own.repo", "s1",
                      "orchard:agent:delegation:begin",
                      identity={"agent": "landscaper", "feature": "feat-a"},
                      body={"subagent": "sub-a"}, mtime=2)
        lines = self._dump()
        sub_line = next(l for l in lines if "sub-a" in l)
        self.assertIn(sidebar.SUBAGENT_GLYPH, sub_line)


# --------------------------------------------------------------------------
# CLI --once, non-tty path — real subprocess with no controlling terminal
# (capture_output pipes, same as DumpCLITests above): must exit non-zero
# with a diagnostic message, never a raw curses traceback. The real-terminal
# path (paints an actual frame and exits 0) is covered in
# tests/test_sidebar_frame.py, which drives it inside a tmux pane.
# --------------------------------------------------------------------------

class OnceCLINonTtyTests(unittest.TestCase):
    def test_once_without_a_terminal_exits_nonzero_with_a_message(self):
        proc = subprocess.run(
            [sys.executable, _SIDEBAR_PY, "--once"],
            capture_output=True, text=True, stdin=subprocess.DEVNULL,
        )
        self.assertNotEqual(proc.returncode, 0)
        self.assertNotIn("Traceback", proc.stderr)
        self.assertTrue(proc.stderr.strip())


# --------------------------------------------------------------------------
# watch()'s inotifywait supervision — a dying/killed child must not freeze
# the sidebar (the child is a real `inotifywait` subprocess, killed for
# real; this is a regression test for a defect observed in production).
# --------------------------------------------------------------------------

@unittest.skipUnless(shutil.which("inotifywait"), "inotifywait not installed")
class WatchSupervisorTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.projects_root = Path(self._tmp.name) / "projects"
        self.projects_root.mkdir(parents=True)
        self.events = []
        self._events_lock = threading.Lock()
        self._watch_thread = threading.Thread(
            target=sidebar.watch, args=(self._on_change, self.projects_root),
            daemon=True,
        )
        self._watch_thread.start()
        self.addCleanup(self._kill_child_inotifywaits)

    def _on_change(self, fleet) -> None:
        with self._events_lock:
            self.events.append(fleet)

    def _event_count(self) -> int:
        with self._events_lock:
            return len(self.events)

    def _wait_for_event_count(self, count, timeout=10):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if self._event_count() >= count:
                return
            time.sleep(0.05)
        self.fail(f"timed out waiting for {count} on_change call(s); "
                   f"got {self._event_count()}")

    def _child_inotifywait_pids(self):
        own_pid = str(os.getpid())
        pids = []
        for entry in os.listdir("/proc"):
            if not entry.isdigit():
                continue
            try:
                status = Path(f"/proc/{entry}/status").read_text()
                cmdline = Path(f"/proc/{entry}/cmdline").read_bytes()
            except OSError:
                continue
            ppid = next(
                (l.split()[1] for l in status.splitlines() if l.startswith("PPid:")),
                None,
            )
            if ppid == own_pid and b"inotifywait" in cmdline:
                pids.append(int(entry))
        return pids

    def _wait_for_inotifywait_child(self, timeout=10):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            pids = self._child_inotifywait_pids()
            if pids:
                return pids
            time.sleep(0.05)
        self.fail("watch() never spawned an inotifywait child")

    def _kill_child_inotifywaits(self):
        for pid in self._child_inotifywait_pids():
            try:
                os.kill(pid, signal.SIGKILL)
            except ProcessLookupError:
                pass

    def test_killed_watcher_child_still_delivers_later_changes(self):
        self._wait_for_event_count(1)  # initial snapshot
        pids = self._wait_for_inotifywait_child()

        for pid in pids:
            os.kill(pid, signal.SIGKILL)

        before = self._event_count()
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline and self._child_inotifywait_pids():
            time.sleep(0.05)  # let the supervisor reap + restart

        (self.projects_root / "own.repo").mkdir()
        _write_event(self.projects_root, "own.repo", "s1",
                      "orchard:agent:lifecycle:starting",
                      identity={"agent": "landscaper", "feature": "feat-a"})

        self._wait_for_event_count(before + 1)

    def test_killed_watcher_child_leaves_no_zombie(self):
        self._wait_for_event_count(1)
        pids = self._wait_for_inotifywait_child()

        for pid in pids:
            os.kill(pid, signal.SIGKILL)

        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            states = []
            for pid in pids:
                try:
                    stat = Path(f"/proc/{pid}/stat").read_text()
                    states.append(stat.rsplit(")", 1)[1].split()[0])
                except FileNotFoundError:
                    states.append(None)
            if all(s in (None, "") for s in states):
                return
            time.sleep(0.05)
        self.fail(f"killed inotifywait child left as a zombie: {states}")


# --------------------------------------------------------------------------
# Pure presentation layer — flatten()/render_lines(), no model dependency.
# --------------------------------------------------------------------------

def _fleet():
    return sidebar.Fleet(repos=[
        sidebar.Repo(
            name="repoA", activity="", status="working", waiting_on_operator=False,
            features=[
                sidebar.Feature(
                    name="feat one", activity="doing work",
                    status="working", waiting_on_operator=False,
                    subagents=[sidebar.Subagent(label="sub-a")],
                ),
            ],
        ),
    ])


class FlattenTests(unittest.TestCase):
    def test_depth_kind_and_target_per_row(self):
        rows = sidebar.flatten(_fleet())
        self.assertEqual(len(rows), 3)

        repo_row, feature_row, sub_row = rows
        self.assertEqual((repo_row.depth, repo_row.kind, repo_row.target),
                         (0, "repo", "repoA"))
        self.assertEqual((feature_row.depth, feature_row.kind, feature_row.target),
                         (1, "feature", "repoA/feat one"))
        self.assertEqual(feature_row.repo_name, "repoA")
        # a subagent row's target is its OWNING feature's target, not its own
        # label -- navigation from a subagent row targets the feature window.
        self.assertEqual((sub_row.depth, sub_row.kind, sub_row.target),
                         (2, "subagent", "repoA/feat one"))
        self.assertTrue(sub_row.is_subagent)
        self.assertFalse(feature_row.is_subagent)
        self.assertFalse(repo_row.is_subagent)

    def test_feature_row_carries_display_grammar_fields(self):
        # flatten() copies the wire-grammar fields onto the Row so the
        # curses draw path never reaches back into the model, plus a
        # `source` pointer for optional fields.
        fleet = _fleet()
        feature = fleet.repos[0].features[0]
        feature.phase = "building"
        feature.progress_pct = 62
        feature.subagents_running = 3
        feature.subagents_queued = 2
        feature.status_word = "writing"

        feature_row = next(r for r in sidebar.flatten(fleet) if r.kind == "feature")
        self.assertEqual(feature_row.phase, "building")
        self.assertEqual(feature_row.progress_pct, 62)
        self.assertEqual(feature_row.subagents_running, 3)
        self.assertEqual(feature_row.subagents_queued, 2)
        self.assertEqual(feature_row.status_word, "writing")
        self.assertIs(feature_row.source, feature)

    def test_repo_without_session_is_skipped_entirely(self):
        # sidebar-titling item 3: an empty project (no live session) has
        # nothing to show -- header AND group both disappear.
        fleet = sidebar.Fleet(repos=[
            sidebar.Repo(name="empty-repo", activity="", status="idle",
                         waiting_on_operator=False, has_session=False),
        ])
        self.assertEqual(sidebar.flatten(fleet), [])

    def test_only_repos_with_a_session_render(self):
        fleet = sidebar.Fleet(repos=[
            sidebar.Repo(name="a", activity="", status="idle",
                         waiting_on_operator=False, has_session=False),
            sidebar.Repo(name="b", activity="", status="idle",
                         waiting_on_operator=False, has_session=True),
        ])
        rows = sidebar.flatten(fleet)
        self.assertEqual([r.target for r in rows], ["b"])

    def test_done_features_sort_first_within_their_repo_group(self):
        # sidebar-titling item 7: done-first, stable sort -- relative order
        # among the still-live features (and among the done ones) is kept.
        fleet = sidebar.Fleet(repos=[
            sidebar.Repo(name="r", activity="", status="idle",
                         waiting_on_operator=False, features=[
                sidebar.Feature(name="a-working", activity="", status="working",
                                 waiting_on_operator=False),
                sidebar.Feature(name="b-done", activity="", status="done",
                                 waiting_on_operator=False),
                sidebar.Feature(name="c-idle", activity="", status="idle",
                                 waiting_on_operator=False),
                sidebar.Feature(name="d-done", activity="", status="done",
                                 waiting_on_operator=False),
            ]),
        ])
        feature_rows = [r for r in sidebar.flatten(fleet) if r.kind == "feature"]
        self.assertEqual(
            [r.label for r in feature_rows],
            ["b-done", "d-done", "a-working", "c-idle"],
        )


class RenderLinesTests(unittest.TestCase):
    def test_status_emoji_per_feature_row(self):
        # status glyphs live on FEATURE rows -- a repo header carries none
        # (sidebar-titling item 4). Looked up by which line contains the
        # feature's name rather than by position, since done-first sorting
        # (item 7) reorders the "done" row ahead of the others.
        statuses = ["working", "waiting", "idle", "awaiting_agent", "stale", "done", "failed"]
        fleet = sidebar.Fleet(repos=[
            sidebar.Repo(name="r", activity="", status="idle",
                         waiting_on_operator=False, features=[
                sidebar.Feature(name=s, activity="", status=s, waiting_on_operator=False)
                for s in statuses
            ]),
        ])
        lines = sidebar.render_lines(fleet, width=64)
        for status in statuses:
            line = next(l for l in lines if status in l)
            self.assertIn(sidebar.STATUS_EMOJI[status], line)

    def test_repo_header_has_no_leading_status_glyph(self):
        fleet = _fleet()  # repo status="working"
        lines = sidebar.render_lines(fleet, width=64)
        for glyph in sidebar.STATUS_EMOJI.values():
            self.assertNotIn(glyph, lines[0])

    def test_feature_row_renders_the_name_without_a_repo_prefix(self):
        # the mock's feature row shows only the feature's own name -- the
        # repo is already named by the header block above its group.
        lines = sidebar.render_lines(_fleet(), width=64)
        self.assertIn("feat one", lines[1])
        self.assertNotIn("repoA/feat one", lines[1])

    def test_done_feature_row_shows_check_and_percentage(self):
        fleet = _fleet()
        fleet.repos[0].features[0].status = "done"
        fleet.repos[0].features[0].progress_pct = 100
        lines = sidebar.render_lines(fleet, width=64)
        self.assertIn(sidebar.STATUS_EMOJI["done"], lines[1])
        self.assertIn("100%", lines[1])

    def test_done_and_failed_glyphs_are_distinct(self):
        # explicit operator correction: never the same encoding for done vs
        # failed ("can't put green for fail, same as you can't have green
        # and green at a traffic light")
        self.assertNotEqual(sidebar.STATUS_EMOJI["done"], sidebar.STATUS_EMOJI["failed"])

    def test_idle_waiting_awaiting_agent_and_stale_intentionally_share_the_hollow_circle(self):
        # visual contract. "waiting"/"awaiting_agent" are unreachable from
        # build_model() today (no blocked/notify_user signal exists in the
        # new grammar) but still part of the STATUS_EMOJI vocabulary
        # render_lines() honours defensively; "stale" IS reachable (a
        # session with no event inside ACTIVE_WINDOW_SECONDS and no
        # terminal outcome — retention ruling, 2026-07-25 revision).
        self.assertEqual(sidebar.STATUS_EMOJI["idle"], "○")
        self.assertEqual(sidebar.STATUS_EMOJI["waiting"], "○")
        self.assertEqual(sidebar.STATUS_EMOJI["awaiting_agent"], "○")
        self.assertEqual(sidebar.STATUS_EMOJI["stale"], "○")

    def test_working_done_and_failed_glyphs_stay_distinct_from_each_other_and_the_circle(self):
        distinguishable = {
            sidebar.STATUS_EMOJI["working"], sidebar.STATUS_EMOJI["done"],
            sidebar.STATUS_EMOJI["failed"], sidebar.STATUS_EMOJI["idle"],
        }
        self.assertEqual(len(distinguishable), 4)

    def test_no_animation_same_state_renders_identically_across_calls(self):
        # a repeated render of the SAME fleet must be byte-identical -- the
        # band sweep and every other display-grammar addition is
        # curses-only (see render_lines()'s docstring).
        fleet = _fleet()
        first = sidebar.render_lines(fleet, width=64)
        second = sidebar.render_lines(fleet, width=64)
        third = sidebar.render_lines(fleet, width=64)
        self.assertEqual(first, second)
        self.assertEqual(second, third)

    def test_subagent_row_shows_presence_glyph(self):
        # sidebar-titling item 4: presence in the model is the only
        # verifiable subagent state -- a filled circle, never the "working"
        # glyph (an unverifiable claim) and never an "idle" counterpart.
        lines = sidebar.render_lines(_fleet(), width=64)
        self.assertIn(sidebar.SUBAGENT_GLYPH, lines[2])
        self.assertNotIn(sidebar.STATUS_EMOJI["working"], lines[2])
        # identical on a second call -- no spinner advance in the pure path
        lines_again = sidebar.render_lines(_fleet(), width=64)
        self.assertEqual(lines[2], lines_again[2])

    def test_indentation_increases_with_depth(self):
        lines = sidebar.render_lines(_fleet(), width=64)
        # strip the leading selection-marker column (always ' ' or '>')
        bodies = [line[1:] for line in lines]
        indents = [len(b) - len(b.lstrip(" ")) for b in bodies]
        self.assertEqual(indents, [0, 2, 4])

    def test_selected_row_has_leading_marker(self):
        lines = sidebar.render_lines(_fleet(), selected=1, width=64)
        self.assertTrue(lines[1].startswith(">"))
        self.assertTrue(lines[0].startswith(" "))
        self.assertTrue(lines[2].startswith(" "))

    def test_lines_truncated_to_width(self):
        lines = sidebar.render_lines(_fleet(), width=6)
        for line in lines:
            self.assertLessEqual(len(line), 6)


def _many_repos_fleet(n):
    """A fleet with exactly `n` rows — one repo row each, no features/subs —
    so row count is trivial to reason about in scroll-offset tests."""
    return sidebar.Fleet(repos=[
        sidebar.Repo(name=f"repo{i}", activity="", status="idle", waiting_on_operator=False)
        for i in range(n)
    ])


class ScrollOffsetTests(unittest.TestCase):
    """sidebar-polish item 3 resolution: scroll-follows-selection viewport
    clamping, the pure logic behind the curses draw loop's persisted
    scroll offset."""

    def test_no_scroll_when_all_rows_fit_the_viewport(self):
        self.assertEqual(sidebar.clamp_scroll_offset(0, 0, 5, 5), 0)
        self.assertEqual(sidebar.clamp_scroll_offset(3, 4, 5, 8), 0)

    def test_selection_below_viewport_shifts_offset_down(self):
        offset = sidebar.clamp_scroll_offset(0, 5, 10, 3)
        self.assertEqual(offset, 3)  # window becomes [3, 6) -> 5 is last visible

    def test_selection_above_viewport_shifts_offset_up(self):
        offset = sidebar.clamp_scroll_offset(4, 2, 10, 3)
        self.assertEqual(offset, 2)

    def test_selection_inside_viewport_leaves_offset_untouched(self):
        offset = sidebar.clamp_scroll_offset(4, 5, 10, 3)
        self.assertEqual(offset, 4)

    def test_offset_never_negative(self):
        offset = sidebar.clamp_scroll_offset(-7, 0, 10, 3)
        self.assertGreaterEqual(offset, 0)
        self.assertEqual(offset, 0)

    def test_offset_never_scrolls_past_showing_the_last_row(self):
        offset = sidebar.clamp_scroll_offset(0, 9, 10, 3)
        self.assertEqual(offset, 7)  # window [7, 10) shows the last row
        offset = sidebar.clamp_scroll_offset(50, 9, 10, 3)
        self.assertEqual(offset, 7)

    def test_render_lines_windows_to_offset_and_height(self):
        fleet = _many_repos_fleet(10)
        lines = sidebar.render_lines(fleet, selected=5, width=32, offset=0, height=3)
        self.assertEqual(len(lines), 3)
        self.assertIn("repo3", lines[0])
        self.assertIn("repo4", lines[1])
        self.assertIn("repo5", lines[2])
        self.assertTrue(lines[2].startswith(">"))  # repo5 is selected

    def test_render_lines_small_fleet_is_not_windowed(self):
        fleet = _many_repos_fleet(2)
        lines = sidebar.render_lines(fleet, selected=1, width=32, offset=0, height=5)
        self.assertEqual(len(lines), 2)  # fewer rows than height -- no scroll

    def test_render_lines_without_height_is_unwindowed(self):
        fleet = _many_repos_fleet(10)
        lines = sidebar.render_lines(fleet, selected=9, width=32)
        self.assertEqual(len(lines), 10)


class TruncateEllipsisTests(unittest.TestCase):
    def test_short_text_is_unaffected(self):
        self.assertEqual(sidebar._truncate("short", 10), "short")

    def test_long_text_ends_with_ellipsis_not_a_hard_cut(self):
        text = "agent-closing Done, awaiting operator"
        truncated = sidebar._truncate(text, 12)
        self.assertEqual(len(truncated), 12)
        self.assertTrue(truncated.endswith(sidebar.ELLIPSIS))
        self.assertEqual(truncated, text[:11] + sidebar.ELLIPSIS)

    def test_ellipsis_counts_toward_width_budget(self):
        truncated = sidebar._truncate("abcdefghij", 5)
        self.assertEqual(len(truncated), 5)
        self.assertTrue(truncated.endswith(sidebar.ELLIPSIS))


class FeatureRowLayoutTests(unittest.TestCase):
    """glyph + name drawn over the progress fill, right-aligned dim
    percentage. `_feature_row_layout` is the single source of truth shared
    by the plain-text compose and the curses per-column painter."""

    def test_compose_feature_row_text_lays_out_glyph_name_and_percentage(self):
        text = sidebar.compose_feature_row_text("⠧", "sidebar titling", 62, 27)
        self.assertTrue(text.startswith("⠧ sidebar titling"))
        self.assertTrue(text.endswith("62%"))
        self.assertEqual(len(text), 27)

    def test_badge_is_inserted_before_the_percentage(self):
        # the badge parameter itself is retained by _feature_row_layout for
        # any future caller -- render_lines() never passes one today (open-
        # question badges are retired, see module docstring).
        text = sidebar.compose_feature_row_text("○", "focus returning", 40, 40, badge="?1")
        self.assertIn("?1 40%", text)

    def test_long_name_is_truncated_before_the_tail_is_sacrificed(self):
        text = sidebar.compose_feature_row_text(
            "⠧", "a very very long feature name indeed", 62, 24,
        )
        self.assertTrue(text.endswith("62%"))
        self.assertEqual(len(text), 24)

    def test_layout_pad_width_fills_exactly_to_the_requested_width(self):
        glyph, shown_name, pad_width, badge_text, pct_text = sidebar._feature_row_layout(
            "✓", "bloomer v1", 100, 27, None,
        )
        used = len(glyph) + 1 + len(shown_name) + pad_width + len(badge_text) + len(pct_text)
        self.assertEqual(used, 27)


class FillColsTests(unittest.TestCase):
    def test_zero_percent_fills_nothing(self):
        self.assertEqual(sidebar.fill_cols(0, 27), 0)

    def test_hundred_percent_fills_the_whole_width(self):
        self.assertEqual(sidebar.fill_cols(100, 27), 27)

    def test_partial_percent_rounds_to_nearest_column(self):
        self.assertEqual(sidebar.fill_cols(62, 27), round(27 * 62 / 100))
        self.assertEqual(sidebar.fill_cols(50, 10), 5)


class BandSweepTests(unittest.TestCase):
    """The bidirectional lifted-band sweep -- band width (abs(col-pos)<=2),
    a triangular wave over [0, span], and lifted colour = lerp(fill, white,
    0.18)."""

    def test_band_position_ramps_up_then_back_down(self):
        span = 5
        positions = [sidebar.band_position(t, span) for t in range(2 * span + 1)]
        self.assertEqual(positions, [0, 1, 2, 3, 4, 5, 4, 3, 2, 1, 0])

    def test_band_position_is_periodic(self):
        span = 4
        first_cycle = [sidebar.band_position(t, span) for t in range(2 * span)]
        second_cycle = [sidebar.band_position(t + 2 * span, span) for t in range(2 * span)]
        self.assertEqual(first_cycle, second_cycle)

    def test_band_span_is_never_less_than_one(self):
        self.assertEqual(sidebar.band_span(0), 1)
        self.assertEqual(sidebar.band_span(1), 1)
        self.assertEqual(sidebar.band_span(6), 5)

    def test_band_column_colour_is_lifted_only_within_two_columns_of_the_band(self):
        fill = (40, 31, 54)
        pos = 10
        self.assertEqual(sidebar.band_column_colour(pos, pos, 27, fill), sidebar.lifted_fill_colour(fill))
        self.assertEqual(sidebar.band_column_colour(pos + 2, pos, 27, fill), sidebar.lifted_fill_colour(fill))
        self.assertEqual(sidebar.band_column_colour(pos + 3, pos, 27, fill), fill)

    def test_band_column_colour_is_none_past_travel_end(self):
        self.assertIsNone(sidebar.band_column_colour(20, 10, 20, (40, 31, 54)))

    def test_lifted_fill_colour_is_18_percent_toward_white(self):
        fill = (40, 31, 54)
        self.assertEqual(sidebar.lifted_fill_colour(fill), sidebar.lerp(fill, sidebar.WHITE, 0.18))


class SmallCapsTests(unittest.TestCase):
    def test_building_matches_the_mocks_literal_small_caps(self):
        self.assertEqual(sidebar.small_caps("building"), "ʙᴜɪʟᴅɪɴɢ")

    def test_releasing_converts_every_letter(self):
        self.assertEqual(sidebar.small_caps("releasing"), "ʀᴇʟᴇᴀꜱɪɴɢ")

    def test_non_letters_pass_through_unchanged(self):
        self.assertEqual(sidebar.small_caps("a b-c"), "ᴀ ʙ-ᴄ")


class IdentityLineTests(unittest.TestCase):
    """"status_word plain ⋮ role dim-italic ⋮ model coloured", glued with
    NBSP around ⋮, model truncated rather than ever wrapped alone."""

    def test_full_identity_glues_segments_with_nbsp_around_the_separator(self):
        text = sidebar.identity_line_text("writing", "architect", "opus-4.8", 100)
        sep = sidebar.NBSP + "⋮" + sidebar.NBSP
        self.assertEqual(text, "writing" + sep + "architect" + sep + "opus-4.8")

    def test_model_is_truncated_to_the_remaining_room_not_wrapped(self):
        doing, role, model = sidebar.compose_identity_line("writing", "architect", "opus-4.8", 24)
        self.assertEqual(doing, "writing")
        self.assertEqual(role, "architect")
        self.assertTrue(model == "" or "opus-4.8".startswith(model))
        self.assertNotIn("\n", model)

    def test_role_none_omits_the_role_segment_entirely(self):
        doing, role, model = sidebar.compose_identity_line("writing", None, "opus-4.8", 100)
        self.assertEqual(role, "")
        text = sidebar.identity_line_text("writing", None, "opus-4.8", 100)
        self.assertNotIn(sidebar.NBSP + "⋮" + sidebar.NBSP + sidebar.NBSP, text)
        self.assertIn("opus-4.8", text)

    def test_model_none_omits_the_model_segment_entirely(self):
        text = sidebar.identity_line_text("writing", "architect", None, 100)
        self.assertEqual(text, "writing" + sidebar.NBSP + "⋮" + sidebar.NBSP + "architect")

    def test_model_tier_colour_keys_off_the_family_prefix(self):
        self.assertEqual(sidebar.model_tier_colour("opus-4.8"), sidebar.MODEL_TIERS["opus"])
        self.assertEqual(sidebar.model_tier_colour("sonnet-5"), sidebar.MODEL_TIERS["sonnet"])
        self.assertEqual(sidebar.model_tier_colour(None), sidebar.TEXT)
        self.assertEqual(sidebar.model_tier_colour("unknown-model"), sidebar.TEXT)


class PhaseChecklistTests(unittest.TestCase):
    """Five-phase vertical checklist (done / active / todo) -- pure helper,
    unreachable from build_model() today (phase has no source in the new
    grammar and stays None; see module docstring) but still exercised
    directly since the function is still exported and used by the curses
    decoration path."""

    def test_phases_before_the_active_one_are_done(self):
        states = dict(sidebar.phase_states("building"))
        self.assertEqual(states["ideation"], "done")
        self.assertEqual(states["scoping"], "done")
        self.assertEqual(states["designing"], "done")
        self.assertEqual(states["building"], "active")
        self.assertEqual(states["releasing"], "todo")

    def test_all_phases_are_todo_when_no_phase_is_active(self):
        states = dict(sidebar.phase_states(None))
        self.assertTrue(all(state == "todo" for state in states.values()))

    def test_unknown_phase_name_is_treated_as_no_active_phase(self):
        states = dict(sidebar.phase_states("not-a-real-phase"))
        self.assertTrue(all(state == "todo" for state in states.values()))

    def test_phase_order_matches_the_canonical_five_phases(self):
        words = [word for word, _state in sidebar.phase_states("scoping")]
        self.assertEqual(words, list(sidebar.PHASES))

    def test_phase_mark_per_state(self):
        self.assertEqual(sidebar.phase_mark("done"), "●")
        self.assertEqual(sidebar.phase_mark("active"), "⠧")
        self.assertEqual(sidebar.phase_mark("todo"), "○")

    def test_inline_dot_counts_running_then_queued(self):
        self.assertEqual(sidebar.phase_dot_suffix(3, 2), "●●●○○")
        self.assertEqual(sidebar.phase_dot_suffix(0, 0), "")
        self.assertEqual(sidebar.phase_dot_suffix(1, 0), "●")
        self.assertEqual(sidebar.phase_dot_suffix(0, 1), "○")


class FooterLinesTests(unittest.TestCase):
    """footer_lines()/done_footer_line() are pure formatters that still
    exist in sidebar.py, unchanged; build_model() never populates
    age/worked/tokens/dollars (see module docstring), so these are exercised
    with synthetic sources rather than anything build_model() produces."""

    def test_footer_omitted_entirely_when_no_data_is_available(self):
        feature = sidebar.Feature(name="f", activity="", status="working",
                                   waiting_on_operator=False)
        self.assertEqual(sidebar.footer_lines(feature), [])

    def test_footer_omitted_when_source_is_none(self):
        self.assertEqual(sidebar.footer_lines(None), [])

    def test_footer_renders_both_lines_when_all_four_values_are_present(self):
        class _Stats:
            age = "3h12"
            worked = "1h47"
            tokens = "212k"
            dollars = "4.12"

        lines = sidebar.footer_lines(_Stats())
        self.assertEqual(lines, ["⏱ 3h12 ⋮ worked 1h47", "⚡ 212k ⋮ $4.12"])

    def test_footer_first_line_needs_both_age_and_worked(self):
        class _PartialStats:
            age = "3h12"
            worked = None
            tokens = "212k"
            dollars = "4.12"

        lines = sidebar.footer_lines(_PartialStats())
        self.assertEqual(lines, ["⚡ 212k ⋮ $4.12"])


class DoneFooterLineTests(unittest.TestCase):
    def test_composes_tokens_dollars_and_age_in_mock_order(self):
        class _Stats:
            tokens = "384k"
            dollars = "7.90"
            age = "6h02"

        self.assertEqual(sidebar.done_footer_line(_Stats()), "⚡ 384k ⋮ $7.90 ⋮ 6h02")

    def test_omitted_when_source_is_none(self):
        self.assertIsNone(sidebar.done_footer_line(None))

    def test_omitted_when_no_value_is_available(self):
        feature = sidebar.Feature(name="f", activity="", status="done",
                                   waiting_on_operator=False)
        self.assertIsNone(sidebar.done_footer_line(feature))

    def test_renders_with_only_age_when_tokens_and_dollars_are_absent(self):
        class _AgeOnly:
            tokens = None
            dollars = None
            age = "6h02"

        self.assertEqual(sidebar.done_footer_line(_AgeOnly()), "6h02")

    def test_renders_with_only_tokens_and_dollars_when_age_is_absent(self):
        class _StatsOnly:
            tokens = "384k"
            dollars = "7.90"
            age = None

        self.assertEqual(sidebar.done_footer_line(_StatsOnly()), "⚡ 384k ⋮ $7.90")

    def test_dollars_alone_without_tokens_never_renders(self):
        class _DollarsOnly:
            tokens = None
            dollars = "7.90"
            age = None

        self.assertIsNone(sidebar.done_footer_line(_DollarsOnly()))


class RepoHueTests(unittest.TestCase):
    """Each repo gets a fixed SOLID hue triple, not a gradient.
    `orchids`/`signmc` get their named triple (case-insensitive); everything
    else gets a stable, repeatable triple derived from the fallback palette."""

    def test_orchids_maps_to_the_mocks_exact_triple(self):
        self.assertEqual(sidebar._repo_hue("orchids"), sidebar.REPO_HUES["orchids"])
        self.assertEqual(sidebar.REPO_HUES["orchids"]["header"], (0x2C, 0x18, 0x3E))
        self.assertEqual(sidebar.REPO_HUES["orchids"]["fill"], (0x28, 0x1F, 0x36))
        self.assertEqual(sidebar.REPO_HUES["orchids"]["accent"], (0xAC, 0x88, 0xD6))

    def test_signmc_maps_to_the_mocks_exact_triple(self):
        self.assertEqual(sidebar._repo_hue("signmc"), sidebar.REPO_HUES["signmc"])
        self.assertEqual(sidebar.REPO_HUES["signmc"]["header"], (0x09, 0x2A, 0x2D))
        self.assertEqual(sidebar.REPO_HUES["signmc"]["fill"], (0x16, 0x2A, 0x2E))
        self.assertEqual(sidebar.REPO_HUES["signmc"]["accent"], (0x6E, 0xB4, 0xB0))

    def test_named_hue_match_is_case_insensitive(self):
        self.assertEqual(sidebar._repo_hue("Orchids"), sidebar.REPO_HUES["orchids"])
        self.assertEqual(sidebar._repo_hue("SIGNMC"), sidebar.REPO_HUES["signmc"])

    def test_unknown_repo_gets_a_stable_repeatable_fallback_triple(self):
        first = sidebar._repo_hue("some-other-repo")
        second = sidebar._repo_hue("some-other-repo")
        self.assertEqual(first, second)
        self.assertIn(first["header"], sidebar.FALLBACK_HEADER_HUES)

    def test_unknown_repo_never_collides_with_a_named_hue(self):
        hue = sidebar._repo_hue("some-other-repo")
        named_headers = {h["header"] for h in sidebar.REPO_HUES.values()}
        self.assertNotIn(hue["header"], named_headers)

    def test_different_unknown_repos_can_get_different_triples(self):
        hues = {sidebar._repo_hue(f"repo-{i}")["header"] for i in range(4)}
        self.assertGreater(len(hues), 1)


class Xterm256Tests(unittest.TestCase):
    def test_black_maps_to_cube_origin(self):
        self.assertEqual(sidebar._rgb_to_xterm256((0, 0, 0)), 16)

    def test_white_maps_to_cube_far_corner(self):
        self.assertEqual(sidebar._rgb_to_xterm256((255, 255, 255)), 231)

    def test_saturated_colour_maps_into_the_colour_cube_range(self):
        for rgb in (sidebar.REPO_HUES["orchids"]["accent"], sidebar.REPO_HUES["signmc"]["accent"]):
            index = sidebar._rgb_to_xterm256(rgb)
            self.assertGreaterEqual(index, 16)
            self.assertLessEqual(index, 231)

    def test_every_repo_hue_maps_into_a_valid_xterm256_index(self):
        for hue in list(sidebar.REPO_HUES.values()):
            for rgb in hue.values():
                index = sidebar._rgb_to_xterm256(rgb)
                self.assertGreaterEqual(index, 16)
                self.assertLessEqual(index, 255)

    def test_neutral_gray_maps_into_the_grayscale_ramp(self):
        index = sidebar._rgb_to_xterm256((128, 128, 128))
        self.assertGreaterEqual(index, 232)
        self.assertLessEqual(index, 255)

    def test_orchids_header_purple_maps_into_the_colour_cube_not_gray(self):
        # regression: this dark, desaturated purple used to lose to the
        # grayscale ramp on pure distance (788 vs 3601) despite having real
        # chroma — the chroma gate must force it into the cube instead.
        index = sidebar._rgb_to_xterm256(sidebar.REPO_HUES["orchids"]["header"])
        self.assertGreaterEqual(index, 16)
        self.assertLessEqual(index, 231)

    def test_genuinely_neutral_colour_still_maps_to_gray_ramp(self):
        index = sidebar._rgb_to_xterm256((60, 60, 60))
        self.assertGreaterEqual(index, 232)
        self.assertLessEqual(index, 255)


class RoleEmojiTests(unittest.TestCase):
    def test_known_roles_map_to_their_emoji(self):
        self.assertEqual(sidebar.ROLE_EMOJI["gardener"], "🌳")
        self.assertEqual(sidebar.ROLE_EMOJI["landscaper"], "🌿")
        self.assertEqual(sidebar.ROLE_EMOJI["sower"], "🌱")
        self.assertEqual(sidebar.ROLE_EMOJI["groundskeeper"], "🧹")
        self.assertEqual(sidebar.ROLE_EMOJI["courier"], "📮")
        self.assertEqual(sidebar.ROLE_EMOJI["bloomer"], "🌸")

    def test_role_emoji_helper_returns_none_without_crashing(self):
        self.assertIsNone(sidebar.role_emoji("orchestrator"))
        self.assertIsNone(sidebar.role_emoji("architect"))
        self.assertIsNone(sidebar.role_emoji("unknown-role"))
        self.assertIsNone(sidebar.role_emoji(None))

    def test_location_badges_are_exported(self):
        self.assertEqual(sidebar.LOCATION_BADGES["local"], "💻")
        self.assertEqual(sidebar.LOCATION_BADGES["cloud"], "☁️")


class HeaderLineTests(unittest.TestCase):
    def test_header_line_centres_title(self):
        line = sidebar.render_header_line("orchids", 15)
        self.assertEqual(len(line), 15)
        self.assertIn("orchids", line)
        self.assertEqual(line.strip(), "orchids")

    def test_header_line_truncates_with_ellipsis_when_too_narrow(self):
        line = sidebar.render_header_line("a very long project title", 10)
        self.assertEqual(len(line), 10)
        self.assertTrue(line.endswith(sidebar.ELLIPSIS))


class DirectColourTests(unittest.TestCase):
    """`_select_display_term` and friends -- the TERM upgrade that lets
    ncurses accept exact RGB as colour numbers on a direct-colour terminal,
    bypassing `_rgb_to_xterm256` entirely. `_terminfo_has_direct_colour` is
    stubbed rather than relying on this host's terminfo database."""

    def test_rgb_to_direct_colour_id_packs_rgb_as_int(self):
        self.assertEqual(sidebar._rgb_to_direct_colour_id((0x2C, 0x18, 0x3E)), 0x2C183E)

    def test_direct_term_name_upgrades_known_256color_terms(self):
        self.assertEqual(sidebar._direct_term_name("tmux-256color"), "tmux-direct")
        self.assertEqual(sidebar._direct_term_name("xterm-256color"), "xterm-direct")

    def test_direct_term_name_none_for_non_256color_term(self):
        self.assertIsNone(sidebar._direct_term_name("screen"))
        self.assertIsNone(sidebar._direct_term_name("xterm-direct"))

    def test_truecolor_advertised_reads_colorterm(self):
        with mock.patch.dict(os.environ, {"COLORTERM": "truecolor"}):
            self.assertTrue(sidebar._truecolor_advertised())
        with mock.patch.dict(os.environ, {"COLORTERM": ""}):
            self.assertFalse(sidebar._truecolor_advertised())

    def test_select_display_term_upgrades_when_truecolor_and_entry_exists(self):
        with mock.patch.dict(os.environ, {"COLORTERM": "truecolor"}), \
             mock.patch.object(sidebar, "_terminfo_has_direct_colour", return_value=True):
            self.assertEqual(sidebar._select_display_term("tmux-256color"), "tmux-direct")

    def test_select_display_term_unchanged_without_truecolor(self):
        with mock.patch.dict(os.environ, {"COLORTERM": ""}):
            self.assertEqual(sidebar._select_display_term("tmux-256color"), "tmux-256color")

    def test_select_display_term_unchanged_when_entry_missing(self):
        with mock.patch.dict(os.environ, {"COLORTERM": "truecolor"}), \
             mock.patch.object(sidebar, "_terminfo_has_direct_colour", return_value=False):
            self.assertEqual(sidebar._select_display_term("tmux-256color"), "tmux-256color")


class PrivateHelperTests(unittest.TestCase):
    """`_repo_display_name`/`_is_bare_uuid` -- small private pure helpers
    the model layer above already exercises indirectly; covered directly
    here too since they're cheap and easy to get subtly wrong."""

    def test_repo_display_name_splits_on_first_dot(self):
        self.assertEqual(sidebar._repo_display_name("owner.repo"), "repo")

    def test_repo_display_name_without_dot_is_unchanged(self):
        self.assertEqual(sidebar._repo_display_name("bare-slug"), "bare-slug")

    def test_is_bare_uuid_matches_a_real_uuid(self):
        self.assertTrue(sidebar._is_bare_uuid("3fa85f64-5717-4562-b3fc-2c963f66afa6"))

    def test_is_bare_uuid_rejects_a_plain_string(self):
        self.assertFalse(sidebar._is_bare_uuid("not-a-uuid-session"))
        self.assertFalse(sidebar._is_bare_uuid(None))
        self.assertFalse(sidebar._is_bare_uuid(""))


class _StubStdscr:
    """Records `addstr` calls instead of touching a real terminal --
    `_draw` only needs `erase`/`getmaxyx`/`refresh`/`addstr` off its
    `stdscr` argument, none of which require curses to be initialised."""

    def __init__(self, height=10, width=40):
        self._height = height
        self._width = width
        self.calls = []

    def erase(self):
        pass

    def getmaxyx(self):
        return self._height, self._width

    def refresh(self):
        pass

    def addstr(self, y, x, text, attr):
        self.calls.append((y, x, text, attr))


def _subagent_row(status, label="sub-a"):
    return sidebar.Row(
        depth=2, kind="subagent", target="feat", label=label,
        status=status, waiting_on_operator=False, is_subagent=True,
    )


class TaskGlyphTests(unittest.TestCase):
    """sidebar-empty-rows step 7 (Decision-058): a completed task must
    visibly read as completed -- its own glyph, distinct from a
    still-working task's presence dot, and done/failed never share one."""

    def test_working_subagent_keeps_presence_glyph(self):
        text = sidebar._row_text(_subagent_row("working"))
        self.assertIn(sidebar.SUBAGENT_GLYPH, text)

    def test_done_subagent_carries_its_own_status_glyph(self):
        text = sidebar._row_text(_subagent_row("done"))
        self.assertIn(sidebar.STATUS_EMOJI["done"], text)
        self.assertNotIn(sidebar.SUBAGENT_GLYPH, text)

    def test_failed_subagent_carries_its_own_status_glyph(self):
        text = sidebar._row_text(_subagent_row("failed"))
        self.assertIn(sidebar.STATUS_EMOJI["failed"], text)
        self.assertNotIn(sidebar.SUBAGENT_GLYPH, text)

    def test_done_and_failed_never_share_a_glyph(self):
        self.assertNotEqual(sidebar.STATUS_EMOJI["done"], sidebar.STATUS_EMOJI["failed"])


class TaskColourExclusivityTests(unittest.TestCase):
    """sidebar-empty-rows step 7: `curses.color_pair(n)` bits from two
    different sources OR together into a third, arbitrary pair -- exactly
    one source may contribute colour-pair bits to a row. A terminal task's
    status colour must win over its agent-identity tint; a working task
    keeps the agent tint so concurrent tasks stay distinguishable."""

    DONE_PAIR = 1 << 8
    FAILED_PAIR = 2 << 8
    WORKING_PAIR = 3 << 8
    AGENT_PAIR_A = 4 << 8
    AGENT_PAIR_B = 5 << 8

    def _draw_one(self, row, agent_colours):
        colour_pairs = {
            "working": self.WORKING_PAIR,
            "done": self.DONE_PAIR | curses.A_BOLD,
            "failed": self.FAILED_PAIR | curses.A_BOLD,
        }
        stdscr = _StubStdscr()
        sidebar._draw(stdscr, [row], selected=-1, offset=0,
                       colour_pairs=colour_pairs, agent_colours=agent_colours,
                       colours=None, tick=0, has_moved=False)
        self.assertEqual(len(stdscr.calls), 1)
        return stdscr.calls[0][3]

    def test_working_task_uses_its_agent_colour_pair(self):
        row = _subagent_row("working", label="sub-a")
        agent_colours = [self.AGENT_PAIR_A, self.AGENT_PAIR_B]
        with mock.patch.object(sidebar, "_agent_colour_index", return_value=0):
            attr = self._draw_one(row, agent_colours)
        self.assertEqual(attr & 0xFF00, self.AGENT_PAIR_A)

    def test_done_task_uses_the_done_pair_not_a_combined_one(self):
        row = _subagent_row("done", label="sub-a")
        agent_colours = [self.AGENT_PAIR_A, self.AGENT_PAIR_B]
        with mock.patch.object(sidebar, "_agent_colour_index", return_value=0):
            attr = self._draw_one(row, agent_colours)
        self.assertEqual(attr & 0xFF00, self.DONE_PAIR)
        self.assertNotEqual(attr & 0xFF00, self.DONE_PAIR | self.AGENT_PAIR_A)

    def test_done_and_working_rows_resolve_to_different_pair_bits(self):
        agent_colours = [self.AGENT_PAIR_A]
        with mock.patch.object(sidebar, "_agent_colour_index", return_value=0):
            done_attr = self._draw_one(_subagent_row("done"), agent_colours)
            working_attr = self._draw_one(_subagent_row("working"), agent_colours)
        self.assertNotEqual(done_attr & 0xFF00, working_attr & 0xFF00)

    def test_failed_task_uses_the_failed_pair_not_the_agent_pair(self):
        row = _subagent_row("failed", label="sub-a")
        agent_colours = [self.AGENT_PAIR_A]
        with mock.patch.object(sidebar, "_agent_colour_index", return_value=0):
            attr = self._draw_one(row, agent_colours)
        self.assertEqual(attr & 0xFF00, self.FAILED_PAIR)


if __name__ == "__main__":
    unittest.main()
