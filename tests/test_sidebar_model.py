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
                  identity=None, status=None, body=None, mtime=None) -> None:
    """`mtime`, when given, overrides the event file's own mtime —
    `build_model()` reads `f.stat().st_mtime`, not any embedded timestamp
    (see `sidebar_model._iter_project_events`), so this is what lets a test
    pin the event timestamps a running-time computation (`Task.
    running_seconds`) derives from, mirroring `tests/test_sidebar.py`'s own
    `_write_event(..., mtime=...)`."""
    project_dir = projects_root / slug
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


class TelemetryFoldTests(_ModelTestCase):
    """M1: `docs/courier-wire.md` §2b's status snapshot (model,
    context_tokens, spend) already rides every post — this is the model
    layer actually reading it onto `Agent`, plus `Task.running_seconds`,
    the event-timestamp-derived running time `sidebar-spec.md` §3 rules
    ("calculations are performed by deterministic script code... never
    through an agent's context")."""

    def test_agent_carries_model_context_tokens_and_spend_from_the_status_snapshot(self):
        _write_event(self.projects_root, self.slug, "s1",
                     "orchard:agent:lifecycle:starting",
                     identity={"agent": "landscaper", "feature": "feat-a"},
                     status={"model": "claude-opus-4-1", "context_tokens": 12345,
                             "spend": {"input_tokens": 100, "output_tokens": 50}})
        agent = self._sole_feature().tasks[0].unstepped_agents[0]
        self.assertEqual(agent.model, "claude-opus-4-1")
        self.assertEqual(agent.context_tokens, 12345)
        self.assertEqual(agent.spend, {"input_tokens": 100, "output_tokens": 50})

    def test_open_task_running_time_is_now_minus_its_earliest_event(self):
        _write_event(self.projects_root, self.slug, "s1",
                     "orchard:agent:lifecycle:starting",
                     identity={"agent": "landscaper", "feature": "feat-a"}, mtime=1000)
        task = self._sole_feature(now=1000 + 90).tasks[0]
        self.assertEqual(task.status, "working")
        self.assertEqual(task.running_seconds, 90)

    def test_terminal_task_running_time_freezes_at_its_own_last_event(self):
        _write_event(self.projects_root, self.slug, "s1",
                     "orchard:agent:lifecycle:starting",
                     identity={"agent": "landscaper", "feature": "feat-a"}, mtime=1000)
        _write_event(self.projects_root, self.slug, "s1",
                     "orchard:agent:outcome:success",
                     identity={"agent": "landscaper", "feature": "feat-a"}, mtime=1090)
        # built long after the task actually finished -- the frozen figure
        # must not keep counting up with wall-clock `now`.
        task = self._sole_feature(now=1000 + 5000).tasks[0]
        self.assertEqual(task.status, "done")
        self.assertEqual(task.running_seconds, 90)

    def test_marker_only_task_has_no_running_time(self):
        # the marker schema records no task start time -- an honest gap,
        # never a guess.
        _write_marker(self.projects_root, self.slug, "feat-a", {
            "schema": 2, "feature": "feat-a",
            "tasks": [{"task": "feat-a", "state": "done", "updated": _now_iso()}],
            "updated": _now_iso(),
        })
        task = self._sole_feature().tasks[0]
        self.assertIsNone(task.started_ts)
        self.assertIsNone(task.running_seconds)


class MultiProjectFoldTests(_ModelTestCase):
    """observability.md's testing bar (restated at sidebar-spec.md §8): AT
    LEAST TWO PROJECTS and TWO FEATURES live at once must fold correctly —
    the (session_id, parent, agent) triple discipline holding throughout,
    and `<owner>.<repo>` plus its `@<branch>` worktree variant folding as
    ONE project (spec §1). Model-level (`build_model()` directly), per the
    M1 brief — the curses/plain-text render side already has its own
    multi-repo coverage (`test_sidebar.py`, `test_sidebar_geometry_sweep.py`)."""

    def test_two_projects_each_carrying_two_features_fold_independently(self):
        # project A: two features, each its own task.
        _write_event(self.projects_root, "owner.repo-a", "a-s1",
                     "orchard:agent:lifecycle:starting",
                     identity={"agent": "landscaper", "feature": "feat-1",
                               "feature_name": "A Feature One"})
        _write_event(self.projects_root, "owner.repo-a", "a-s2",
                     "orchard:agent:lifecycle:starting",
                     identity={"agent": "sower", "feature": "feat-2",
                               "feature_name": "A Feature Two"})
        # project B: two features, each its own task -- session ids
        # deliberately reused verbatim from project A, since session ids
        # are only ever meaningful within their own project's runtime tree
        # and must never fold across projects.
        _write_event(self.projects_root, "owner.repo-b", "a-s1",
                     "orchard:agent:lifecycle:starting",
                     identity={"agent": "groundskeeper", "feature": "feat-1",
                               "feature_name": "B Feature One"})
        _write_event(self.projects_root, "owner.repo-b", "a-s2",
                     "orchard:agent:lifecycle:starting",
                     identity={"agent": "bloomer", "feature": "feat-2",
                               "feature_name": "B Feature Two"})

        fleet = self._build()
        by_repo = {repo.name: repo for repo in fleet.repos}
        self.assertEqual(set(by_repo), {"repo-a", "repo-b"})

        for repo_name, expected_names, expected_roles in (
            ("repo-a", {"A Feature One", "A Feature Two"}, {"landscaper", "sower"}),
            ("repo-b", {"B Feature One", "B Feature Two"}, {"groundskeeper", "bloomer"}),
        ):
            repo = by_repo[repo_name]
            self.assertEqual({f.name for f in repo.features}, expected_names)
            roles = {
                agent.role
                for feature in repo.features
                for task in feature.tasks
                for agent in task.unstepped_agents
            }
            self.assertEqual(roles, expected_roles)

    def test_repo_and_its_branch_worktree_variant_fold_as_one_project(self):
        # `<owner>.<repo>` and `<owner>.<repo>@<branch>` are the SAME
        # project (spec §1) -- one feature posted from each directory must
        # land under one repo row, not two.
        _write_event(self.projects_root, "owner.repo", "main-s1",
                     "orchard:agent:lifecycle:starting",
                     identity={"agent": "gardener", "feature": "feat-main",
                               "feature_name": "Main Feature"})
        _write_event(self.projects_root, "owner.repo@f-worktree", "wt-s1",
                     "orchard:agent:lifecycle:starting",
                     identity={"agent": "landscaper", "feature": "feat-wt",
                               "feature_name": "Worktree Feature"})

        fleet = self._build()
        self.assertEqual(len(fleet.repos), 1)
        repo = fleet.repos[0]
        self.assertEqual(repo.name, "repo")
        self.assertEqual({f.name for f in repo.features}, {"Worktree Feature"})
        # "Main Feature" is folded into the repo HEADER (the gardener
        # session), which is excluded from the features loop by design
        # (`_assemble_repo`) -- it is not a missing fold, it is the header.
        self.assertEqual(repo.role, "gardener")

    def test_same_session_id_in_two_different_projects_never_cross_contaminates(self):
        # session ids are only unique WITHIN a project's own runtime tree;
        # the same literal id in two projects must resolve to two entirely
        # separate agent records, keyed apart by their own project's fold.
        _write_event(self.projects_root, "owner.repo-a", "shared-sid",
                     "orchard:agent:lifecycle:starting",
                     identity={"agent": "landscaper", "feature": "feat-a"})
        _write_event(self.projects_root, "owner.repo-b", "shared-sid",
                     "orchard:agent:outcome:fail",
                     identity={"agent": "sower", "feature": "feat-b"})
        fleet = self._build()
        by_repo = {repo.name: repo for repo in fleet.repos}
        agent_a = by_repo["repo-a"].features[0].tasks[0].unstepped_agents[0]
        agent_b = by_repo["repo-b"].features[0].tasks[0].unstepped_agents[0]
        self.assertEqual(agent_a.role, "landscaper")
        self.assertEqual(agent_a.status, "working")
        self.assertEqual(agent_b.role, "sower")
        self.assertEqual(agent_b.status, "failed")


class M2TelemetryFoldTests(_ModelTestCase):
    """M2: `Agent.effort` (courier-wire.md §2b's `effort` field) and
    `Task.context_tokens` (the most-recently-updated live agent's own
    `context_tokens`, `_task_context_tokens`)."""

    def test_agent_carries_effort_from_the_status_snapshot(self):
        _write_event(self.projects_root, self.slug, "s1",
                     "orchard:agent:lifecycle:starting",
                     identity={"agent": "landscaper", "feature": "feat-a"},
                     status={"model": "claude-opus-4-1", "effort": "high"})
        agent = self._sole_feature().tasks[0].unstepped_agents[0]
        self.assertEqual(agent.effort, "high")

    def test_agent_effort_is_none_when_the_status_snapshot_carries_none(self):
        _write_event(self.projects_root, self.slug, "s1",
                     "orchard:agent:lifecycle:starting",
                     identity={"agent": "landscaper", "feature": "feat-a"},
                     status={"model": "claude-opus-4-1"})
        agent = self._sole_feature().tasks[0].unstepped_agents[0]
        self.assertIsNone(agent.effort)

    def test_task_context_tokens_reads_the_most_recently_updated_live_agent(self):
        # two unstepped agents on the same task, one posting later than
        # the other -- the task's own context figure follows the FRESHER
        # one, not the first one folded.
        _write_event(self.projects_root, self.slug, "s-old",
                     "orchard:agent:lifecycle:starting",
                     identity={"agent": "landscaper", "feature": "feat-a"},
                     status={"context_tokens": 11111}, mtime=1000)
        _write_event(self.projects_root, self.slug, "s-new",
                     "orchard:agent:lifecycle:starting",
                     identity={"agent": "sower", "feature": "feat-a"},
                     status={"context_tokens": 22222}, mtime=2000)
        task = self._sole_feature(now=3000).tasks[0]
        self.assertEqual(task.context_tokens, 22222)

    def test_task_context_tokens_is_none_when_no_agent_carries_one(self):
        _write_event(self.projects_root, self.slug, "s1",
                     "orchard:agent:lifecycle:starting",
                     identity={"agent": "landscaper", "feature": "feat-a"})
        task = self._sole_feature().tasks[0]
        self.assertIsNone(task.context_tokens)


class WaitingStatusTests(_ModelTestCase):
    """M2: the "waiting" STATUS word (courier-wire.md §4's notify_user-
    removal note — "a waiting agent is STATUS ('waiting')") maps onto
    Decision-058's own waiting glyph state via `_status_for`, closing a
    previously-recorded gap ("no waiting/awaiting_agent variant exists").
    `awaiting_agent` stays deliberately unreachable — its producer word is
    still being settled with the operator (M2 scope guard)."""

    def test_a_status_post_of_the_word_waiting_reads_as_waiting(self):
        _write_event(self.projects_root, self.slug, "s1",
                     "orchard:agent:lifecycle:starting",
                     identity={"agent": "landscaper", "feature": "feat-a"})
        _write_event(self.projects_root, self.slug, "s1",
                     "orchard:agent:status", identity={"agent": "landscaper", "feature": "feat-a"},
                     body="waiting")
        agent = self._sole_feature().tasks[0].unstepped_agents[0]
        self.assertEqual(agent.status, "waiting")

    def test_a_status_word_other_than_waiting_is_not_mistaken_for_it(self):
        _write_event(self.projects_root, self.slug, "s1",
                     "orchard:agent:lifecycle:starting",
                     identity={"agent": "landscaper", "feature": "feat-a"})
        _write_event(self.projects_root, self.slug, "s1",
                     "orchard:agent:status", identity={"agent": "landscaper", "feature": "feat-a"},
                     body="building tree")
        agent = self._sole_feature().tasks[0].unstepped_agents[0]
        self.assertEqual(agent.status, "working")

    def test_a_waiting_agent_still_goes_stale_past_the_active_window(self):
        # Decision-094: staleness is a colour, not a removal -- it
        # overrides a stuck "waiting" activity word the same way it
        # already overrides a stuck lifecycle state.
        _write_event(self.projects_root, self.slug, "s1",
                     "orchard:agent:status", identity={"agent": "landscaper", "feature": "feat-a"},
                     body="waiting", mtime=1000)
        agent = self._sole_feature(
            now=1000 + sidebar_model.ACTIVE_WINDOW_SECONDS + 300,
        ).tasks[0].unstepped_agents[0]
        self.assertEqual(agent.status, "stale")

    def test_waiting_task_status_combines_between_working_and_stale(self):
        # `_combine_status`'s own precedence (failed > working > waiting >
        # stale > idle): a task with one working and one waiting agent
        # still reads "working" as a whole -- the more urgent of the two.
        self.assertEqual(
            sidebar_model._combine_status(["waiting", "working"]), "working",
        )
        self.assertEqual(
            sidebar_model._combine_status(["waiting", "stale"]), "waiting",
        )
        self.assertEqual(sidebar_model._combine_status(["waiting"]), "waiting")


class RepoFooterAggregateTests(_ModelTestCase):
    """M2: `Repo.age`/`worked`/`tokens`/`dollars` (spec §3's `age⏱ vs worked
    + tokens⚡/dollars` footer grammar), computed deterministically from
    this repo's own agent records by `_repo_time_and_tokens`. `dollars`
    rides `orchard_topic.py`'s promoted `status.dollars` field the same way
    `tokens_in`/`tokens_out` do — None whenever no agent record on the repo
    carries one (see `Repo.dollars`'s own docstring in sidebar_model.py)."""

    def test_age_is_now_minus_the_repos_own_earliest_event(self):
        _write_event(self.projects_root, self.slug, "s1",
                     "orchard:agent:lifecycle:starting",
                     identity={"agent": "landscaper", "feature": "feat-a"}, mtime=1000)
        repo = self._build(now=1000 + 3600).repos[0]
        self.assertEqual(repo.age, "1h00")

    def test_worked_is_the_union_of_two_overlapping_agent_spans_not_their_sum(self):
        # agent one: [0, 100]; agent two: [50, 150] -- overlapping by 50s.
        # WORKED must read the union (150s), never the naive sum (200s).
        _write_event(self.projects_root, self.slug, "s-one",
                     "orchard:agent:lifecycle:starting",
                     identity={"agent": "landscaper", "feature": "feat-a"}, mtime=1000)
        _write_event(self.projects_root, self.slug, "s-one",
                     "orchard:agent:outcome:success",
                     identity={"agent": "landscaper", "feature": "feat-a"}, mtime=1100)
        _write_event(self.projects_root, self.slug, "s-two",
                     "orchard:agent:lifecycle:starting",
                     identity={"agent": "sower", "feature": "feat-a"}, mtime=1050)
        _write_event(self.projects_root, self.slug, "s-two",
                     "orchard:agent:outcome:success",
                     identity={"agent": "sower", "feature": "feat-a"}, mtime=1150)
        repo = self._build(now=1150 + 10).repos[0]
        self.assertEqual(repo.worked, "2m")  # 150s, union not 200s (3m20s)

    def test_worked_excludes_the_gap_before_the_first_agent_and_between_agents(self):
        # a real idle stretch between two agents' own spans must not count
        # toward WORKED, even though it counts toward AGE.
        _write_event(self.projects_root, self.slug, "s-one",
                     "orchard:agent:lifecycle:starting",
                     identity={"agent": "landscaper", "feature": "feat-a"}, mtime=1000)
        _write_event(self.projects_root, self.slug, "s-one",
                     "orchard:agent:outcome:success",
                     identity={"agent": "landscaper", "feature": "feat-a"}, mtime=1010)
        _write_event(self.projects_root, self.slug, "s-two",
                     "orchard:agent:lifecycle:starting",
                     identity={"agent": "sower", "feature": "feat-a"}, mtime=5000)
        _write_event(self.projects_root, self.slug, "s-two",
                     "orchard:agent:outcome:success",
                     identity={"agent": "sower", "feature": "feat-a"}, mtime=5010)
        repo = self._build(now=5010).repos[0]
        self.assertEqual(repo.age, "1h06")  # 4010s since the very first event
        self.assertEqual(repo.worked, "20s")  # 10s + 10s, the gap excluded

    def test_tokens_sums_tokens_in_and_out_across_every_agent(self):
        _write_event(self.projects_root, self.slug, "s-one",
                     "orchard:agent:lifecycle:starting",
                     identity={"agent": "landscaper", "feature": "feat-a"},
                     status={"tokens_in": 1000, "tokens_out": 2000})
        _write_event(self.projects_root, self.slug, "s-two",
                     "orchard:agent:lifecycle:starting",
                     identity={"agent": "sower", "feature": "feat-a"},
                     status={"tokens_in": 500, "tokens_out": 500})
        repo = self._build().repos[0]
        self.assertEqual(repo.tokens, "4.0k")  # 1000+2000+500+500

    def test_dollars_stays_none_when_no_agent_record_carries_a_figure(self):
        """`orchard_topic.py`'s `_status()` now promotes `dollars` when the
        wire carries it (docs/courier-wire.md §2b); a fixture event with no
        `dollars` in its `status` block (an unrecognised model, or no
        estimate at all) still leaves it None — never invented."""
        _write_event(self.projects_root, self.slug, "s1",
                     "orchard:agent:lifecycle:starting",
                     identity={"agent": "landscaper", "feature": "feat-a"},
                     status={"tokens_in": 1000, "tokens_out": 2000})
        repo = self._build().repos[0]
        self.assertIsNone(repo.dollars)

    def test_dollars_sums_each_agents_own_latest_figure_across_the_repo(self):
        """Same aggregation convention as `tokens` above — each agent's own
        latest `status.dollars` (already promoted through the wire, not
        computed here), summed across every agent on the repo."""
        _write_event(self.projects_root, self.slug, "s-one",
                     "orchard:agent:lifecycle:starting",
                     identity={"agent": "landscaper", "feature": "feat-a"},
                     status={"tokens_in": 1000, "tokens_out": 2000, "dollars": 1.5})
        _write_event(self.projects_root, self.slug, "s-two",
                     "orchard:agent:lifecycle:starting",
                     identity={"agent": "sower", "feature": "feat-a"},
                     status={"tokens_in": 500, "tokens_out": 500, "dollars": 0.4})
        repo = self._build().repos[0]
        self.assertEqual(repo.dollars, "1.90")

    def test_empty_repo_has_no_age_worked_or_tokens(self):
        _write_marker(self.projects_root, self.slug, "feat-a", {
            "schema": 2, "feature": "feat-a",
            "tasks": [{"task": "feat-a", "state": "done", "updated": _now_iso()}],
            "updated": _now_iso(),
        })
        # a marker-only feature carries no LIVE agent record at all -- the
        # repo footer figures, sourced purely from agent records, are
        # honestly absent, not zero.
        repo = self._build().repos[0]
        self.assertIsNone(repo.age)
        self.assertIsNone(repo.worked)
        self.assertIsNone(repo.tokens)


if __name__ == "__main__":
    unittest.main()
