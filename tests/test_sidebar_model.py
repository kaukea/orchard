"""Marker-as-cache tests for `tools/sidebar_model.py`, importing the model
layer directly (never through `sidebar.py`) so this file's coverage does not
depend on, or collide with, whatever `sidebar.py`'s own layout/render work is
doing concurrently on this branch.

THE RULING under test (operator, 2026-07-27): "The marker should contain a
cache... events supply what is happening NOW, read live. The marker supplies
what REMAINS when nothing is happening." Concretely:

  - a feature/task with no live events still renders off its marker alone
    (Decision-099 — the marker is the durable record of the TASK);
  - a live event for the same task always wins over the marker;
  - nothing agent-shaped (role/model/activity/status) is ever read from a
    marker (live-only, per the module's own `_marker_task_rec`);
  - a FEATURE is not terminal: a new live task under a feature that also has
    a marker-only, terminal sibling task revives both together
    (Decision-106 — "that asymmetry is the entire reason the cache exists").

Per Decision-103 (operator ruling, 2026-07-26: never test code where the
caller and the callee are the same code without another test against static
data validated at feature-writing time), `MarkerStaticFixtureTests` below
drives `build_model()` against the real `<feature-id>.marker` bytes captured
from the live system in `tests/fixtures/` (see `tests/fixtures/PROVENANCE.md`)
— not JSON this test constructs itself. Those exact fixtures
(`marker_feature_schema1_live.json`, `marker_feature_schema2_live.json`) are
otherwise only exercised by the transport-side tests in
`tests/test_orchard_transport.py`, never through the model's own
`build_model()` — this file closes that gap.
"""
import itertools
import json
import os
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

_ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
_TOOLS_DIR = os.path.join(os.path.dirname(_ROOT_DIR), "tools")
if _TOOLS_DIR not in sys.path:
    sys.path.insert(0, _TOOLS_DIR)

import sidebar_model  # noqa: E402

_FIXTURES_DIR = Path(_ROOT_DIR) / "fixtures"

_counter = itertools.count()


def _load_fixture(name: str) -> str:
    return (_FIXTURES_DIR / name).read_text(encoding="utf-8")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _write_marker(projects_root: Path, slug: str, feature_id: str, marker: dict) -> None:
    project_dir = projects_root / slug
    project_dir.mkdir(parents=True, exist_ok=True)
    (project_dir / f"{feature_id}.marker").write_text(json.dumps(marker), encoding="utf-8")


def _install_raw_marker(projects_root: Path, slug: str, feature_id: str, fixture_name: str) -> None:
    """A marker file whose bytes are the literal fixture content — no
    parse-and-reserialize round trip through this test's own code."""
    project_dir = projects_root / slug
    project_dir.mkdir(parents=True, exist_ok=True)
    (project_dir / f"{feature_id}.marker").write_text(_load_fixture(fixture_name), encoding="utf-8")


def _write_event(projects_root: Path, slug: str, sid: str, subject: str, *,
                  identity=None, status=None, body=None) -> None:
    project_dir = projects_root / slug
    project_dir.mkdir(parents=True, exist_ok=True)
    envelope = {"from": f":session:{sid}", "subject": subject}
    if body is not None:
        envelope["body"] = body
    if identity is not None:
        envelope["identity"] = identity
    if status is not None:
        envelope["status"] = status
    (project_dir / f"{sid}.{next(_counter):08d}.json").write_text(
        json.dumps(envelope), encoding="utf-8",
    )


class _ModelTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.projects_root = Path(self._tmp.name) / "projects"
        self.slug = "own.repo"

    def _build(self, now: float | None = None):
        return sidebar_model.build_model(root=self.projects_root, now=now, role_step_map={})

    def _sole_feature(self, now: float | None = None) -> sidebar_model.Feature:
        fleet = self._build(now=now)
        self.assertEqual(len(fleet.repos), 1)
        self.assertEqual(len(fleet.repos[0].features), 1)
        return fleet.repos[0].features[0]


class MarkerOnlyCacheTests(_ModelTestCase):
    """A feature/task with NO live events at all still renders — off its
    marker alone — carrying its persisted terminal state and nothing
    agent-shaped."""

    def test_marker_with_no_live_events_renders_the_task_and_its_terminal_state(self):
        _write_marker(self.projects_root, self.slug, "feat-a", {
            "schema": 2, "feature": "feat-a", "name": "Feature A",
            "tasks": [{"task": "feat-a", "name": "Feature A", "state": "done",
                       "updated": _now_iso()}],
            "updated": _now_iso(),
        })
        feature = self._sole_feature()
        self.assertEqual(feature.name, "Feature A")
        self.assertEqual(feature.status, "done")
        task = feature.tasks[0]
        self.assertEqual(task.status, "done")
        # nothing agent-shaped: no steps, no unstepped agents, no subagents.
        self.assertEqual(task.steps, [])
        self.assertEqual(task.unstepped_agents, [])

    def test_marker_only_failed_task_renders_failed(self):
        _write_marker(self.projects_root, self.slug, "feat-a", {
            "schema": 2, "feature": "feat-a",
            "tasks": [{"task": "feat-a", "state": "failed", "updated": _now_iso()}],
            "updated": _now_iso(),
        })
        self.assertEqual(self._sole_feature().status, "failed")


class LiveEventsTakePrecedenceTests(_ModelTestCase):
    def test_live_event_for_the_same_task_wins_over_its_marker(self):
        _write_marker(self.projects_root, self.slug, "feat-a", {
            "schema": 2, "feature": "feat-a", "name": "stale marker name",
            "tasks": [{"task": "feat-a", "name": "stale marker name",
                       "state": "done", "updated": _now_iso()}],
            "updated": _now_iso(),
        })
        _write_event(self.projects_root, self.slug, "s1",
                     "orchard:agent:lifecycle:starting",
                     identity={"agent": "landscaper", "feature": "feat-a"})
        feature = self._sole_feature()
        # the live "working" status wins over the marker's persisted "done" —
        # a live event for the same task always describes NOW.
        self.assertEqual(feature.status, "working")
        task = feature.tasks[0]
        self.assertEqual(task.unstepped_agents[0].role, "landscaper")

    def test_marker_role_never_leaks_onto_a_live_agent(self):
        # a legacy/foreign `role`-shaped key on a marker task entry must not
        # be read at all -- role is live-only, sourced from the event's own
        # identity, never from the marker.
        _write_marker(self.projects_root, self.slug, "feat-a", {
            "schema": 2, "feature": "feat-a",
            "tasks": [{"task": "feat-a", "role": "architect", "state": "done",
                       "updated": _now_iso()}],
            "updated": _now_iso(),
        })
        _write_event(self.projects_root, self.slug, "s1",
                     "orchard:agent:lifecycle:starting",
                     identity={"agent": "landscaper", "feature": "feat-a"})
        agent = self._sole_feature().tasks[0].unstepped_agents[0]
        self.assertEqual(agent.role, "landscaper")


class FeatureRevivalTests(_ModelTestCase):
    """Decision-106: a TASK is terminal and never reopens, but a FEATURE is
    not — a new task under a feature that already has a marker-only,
    terminal sibling task revives the feature, and the completed sibling
    comes back alongside the new one. This is the entire reason the cache
    exists rather than the marker simply being replaced wholesale by live
    data."""

    def test_a_new_live_task_revives_a_feature_alongside_its_completed_marker_sibling(self):
        _write_marker(self.projects_root, self.slug, "feat-a", {
            "schema": 2, "feature": "feat-a", "name": "Feature A",
            "tasks": [{"task": "task-old", "name": "old task", "state": "done",
                       "updated": _now_iso()}],
            "updated": _now_iso(),
        })
        _write_event(self.projects_root, self.slug, "s1",
                     "orchard:agent:lifecycle:starting",
                     identity={"agent": "landscaper", "feature": "feat-a",
                               "feature_name": "Feature A",
                               "task": "task-new", "task_name": "new task"})
        feature = self._sole_feature()
        self.assertEqual(feature.name, "Feature A")
        task_ids = sorted(t.task_id for t in feature.tasks)
        self.assertEqual(task_ids, ["task-new", "task-old"])
        by_id = {t.task_id: t for t in feature.tasks}
        self.assertEqual(by_id["task-old"].status, "done")
        self.assertEqual(by_id["task-new"].status, "working")
        # the feature as a whole is "working" (not "done") -- not terminal,
        # reopened by the new task (`_combine_status`'s failed>working>
        # stale>idle precedence, "done" only once every child is done).
        self.assertEqual(feature.status, "working")


class MarkerStaticFixtureTests(_ModelTestCase):
    """Decision-103: static-data coverage over marker bytes CAPTURED FROM
    THE LIVE SYSTEM (see `tests/fixtures/PROVENANCE.md`), not JSON this test
    constructs and feeds to its own reader — a round trip between our own
    writer and reader proves only that the two agree with each other. These
    two fixtures are otherwise only exercised by `test_orchard_transport.py`
    (the transport side); neither is currently driven through
    `build_model()` anywhere else."""

    def test_schema2_live_marker_renders_its_task_via_build_model(self):
        marker = json.loads(_load_fixture("marker_feature_schema2_live.json"))
        _install_raw_marker(self.projects_root, "kaukea.orchids",
                             "sidebar-empty-rows", "marker_feature_schema2_live.json")
        task_updated_ts = datetime.fromisoformat(
            marker["tasks"][0]["updated"],
        ).timestamp()
        feature = sidebar_model.build_model(
            root=self.projects_root, now=task_updated_ts + 60, role_step_map={},
        ).repos[0].features[0]
        self.assertEqual(feature.name, marker["name"])
        self.assertEqual(feature.tasks[0].task_id, marker["tasks"][0]["task"])
        # "working" state, well inside the active window -> renders working.
        self.assertEqual(feature.status, "working")
        self.assertEqual(feature.tasks[0].unstepped_agents, [])

    def test_schema1_live_marker_still_parses_via_the_feature_key_fallback(self):
        marker = json.loads(_load_fixture("marker_feature_schema1_live.json"))
        _install_raw_marker(self.projects_root, "kaukea.orchids",
                             "sidebar-empty-rows", "marker_feature_schema1_live.json")
        task_updated_ts = datetime.fromisoformat(
            marker["tasks"][0]["updated"],
        ).timestamp()
        feature = sidebar_model.build_model(
            root=self.projects_root, now=task_updated_ts + 60, role_step_map={},
        ).repos[0].features[0]
        # schema 1 has no top-level `name` in this captured file's tasks[]
        # entry keying, but does carry one at the marker's own top level.
        self.assertEqual(feature.name, marker["name"])
        # schema 1's tasks[] entries key off `feature`, not `task` -- the
        # reader's fallback (`_marker_task_id`) must still resolve an id.
        self.assertEqual(feature.tasks[0].task_id, marker["tasks"][0]["feature"])
        self.assertEqual(feature.status, "working")


if __name__ == "__main__":
    unittest.main()
