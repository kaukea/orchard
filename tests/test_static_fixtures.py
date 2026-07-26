"""Static-data tests for the three contracts this branch (sidebar-empty-rows)
touches: the feature/task marker schema, the orchard event envelope shape,
and the courier-only-transport PreToolUse hook.

OPERATOR RULING (2026-07-26, verbatim): "never test code where the caller
and the callee are the same code without another test with static daata
vaidated at feature riting time". A round-trip test where OUR writer
produces the input OUR reader consumes proves only that the two agree —
if both are wrong in the same way it still passes. That already happened
on this branch: writer and reader agreed on a marker shape the operator
later rejected, and the whole suite stayed green.

Every fixture this module reads lives under `tests/fixtures/` as a real
file captured from the live system on 2026-07-26 and hand-validated then
(see `tests/fixtures/PROVENANCE.md`). NONE of it is constructed here by
calling sidebar.py's, orchard_topic.py's, or courier.py's own writers —
that separation is the entire point of this module. If an assertion below
ever fails, the fixture is not to be adjusted to match the code; the
disagreement is reported as-is.
"""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

_ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
_TOOLS_DIR = os.path.join(os.path.dirname(_ROOT_DIR), "tools")
if _TOOLS_DIR not in sys.path:
    sys.path.insert(0, _TOOLS_DIR)

import sidebar  # noqa: E402

_FIXTURES_DIR = Path(_ROOT_DIR) / "fixtures"
_HOOK = os.path.join(
    os.path.dirname(_ROOT_DIR), "hooks", "courier-only-transport.sh",
)


def _load_fixture(name: str) -> str:
    """Raw text of a captured fixture file — read, never parsed-and-
    reserialized, so what lands on disk for the reader under test is the
    literal captured bytes."""
    return (_FIXTURES_DIR / name).read_text(encoding="utf-8")


def _load_fixture_json(name: str) -> dict:
    return json.loads(_load_fixture(name))


class MarkerFixtureTests(unittest.TestCase):
    """sidebar.py's `build_model()` against real `<feature-id>.marker` files,
    placed on disk exactly as captured — no `_write_marker`-style helper
    that would construct the JSON in Python."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.projects_root = Path(self._tmp.name) / "projects"

    def _install_marker(self, fixture_name: str, slug: str, feature_id: str) -> None:
        project_dir = self.projects_root / slug
        project_dir.mkdir(parents=True, exist_ok=True)
        (project_dir / f"{feature_id}.marker").write_text(
            _load_fixture(fixture_name), encoding="utf-8",
        )

    @staticmethod
    def _marker_task_updated_ts(fixture_name: str) -> float:
        """Epoch seconds for the captured marker's own task `updated` field
        — read from the fixture text itself (never re-derived by calling
        sidebar.py's own writer), so a test can pin `build_model()`'s `now`
        relative to a real captured instant instead of racing the wall
        clock against a fixture that only gets older."""
        marker = json.loads(_load_fixture(fixture_name))
        return datetime.fromisoformat(marker["tasks"][0]["updated"]).timestamp()

    def test_valid_marker_renders_one_working_task_row_with_no_agent_or_subagents(self) -> None:
        # FIXTURE 1 — a real feature/task marker as written to the live
        # tree. No event files exist alongside it. Its own `updated` is a
        # fixed captured instant that only gets further in the past as
        # real time passes, so `now` is pinned just inside
        # ACTIVE_WINDOW_SECONDS of it rather than read from the wall clock
        # — otherwise this assertion would flip to "stale" the moment the
        # fixture's age exceeded the window, regardless of the code under
        # test.
        self._install_marker("marker_valid_task.json", "kaukea.orchids", "sidebar-empty-rows")
        marker_ts = self._marker_task_updated_ts("marker_valid_task.json")

        fleet = sidebar.build_model(root=self.projects_root, now=marker_ts + 300)
        rows = sidebar.flatten(fleet)
        feature_rows = [r for r in rows if r.kind == "feature"]
        subagent_rows = [r for r in rows if r.kind == "subagent"]

        self.assertEqual(len(feature_rows), 1, f"expected exactly one task row, got {feature_rows!r}")
        row = feature_rows[0]
        self.assertEqual(
            row.label,
            "Sidebar empty rows: header renders, zero session rows off the "
            "live orchard tree — check (a) failing",
        )
        self.assertEqual(row.status, "working")
        self.assertIsNone(getattr(row.source, "role", None))
        self.assertIsNone(getattr(row.source, "model", None))
        self.assertEqual(subagent_rows, [])

    def test_valid_marker_task_outside_the_active_window_reads_stale_not_working(self) -> None:
        # Same captured marker, same "working" state — but with `now` past
        # ACTIVE_WINDOW_SECONDS of the marker's own `updated`. Decision-094:
        # staleness is a colour, not a removal, and a marker's own claim of
        # "working" does not override "not heard from in a while".
        self._install_marker("marker_valid_task.json", "kaukea.orchids", "sidebar-empty-rows")
        marker_ts = self._marker_task_updated_ts("marker_valid_task.json")

        fleet = sidebar.build_model(
            root=self.projects_root, now=marker_ts + sidebar.ACTIVE_WINDOW_SECONDS + 300,
        )
        rows = sidebar.flatten(fleet)
        feature_rows = [r for r in rows if r.kind == "feature"]

        self.assertEqual(len(feature_rows), 1, f"expected exactly one task row, got {feature_rows!r}")
        self.assertEqual(feature_rows[0].status, "stale")

    def test_legacy_rejected_marker_renders_only_the_valid_task_no_label_only_no_agent(self) -> None:
        # FIXTURE 2 — a rejected legacy marker shape: a `sessions` block
        # (subagent-shaped) and a `tasks[]` entry with only a `label` (no
        # `feature`), alongside one valid task entry. Neither must resurrect
        # a row.
        self._install_marker(
            "marker_legacy_rejected_sessions.json", "kaukea.orchids", "sidebar-empty-rows",
        )

        fleet = sidebar.build_model(root=self.projects_root)
        rows = sidebar.flatten(fleet)
        feature_rows = [r for r in rows if r.kind == "feature"]
        subagent_rows = [r for r in rows if r.kind == "subagent"]

        self.assertEqual(len(feature_rows), 1, f"expected exactly one row, got {feature_rows!r}")
        row = feature_rows[0]
        self.assertEqual(row.label, "Sidebar empty rows")
        self.assertNotEqual(row.label, "verify-task-persist")
        self.assertIsNone(getattr(row.source, "role", None))
        self.assertIsNone(getattr(row.source, "model", None))
        self.assertEqual(subagent_rows, [])


class EventEnvelopeFixtureTests(unittest.TestCase):
    """sidebar.py's `_fold_sessions()` against two real orchard event
    envelopes with genuinely different key sets — a topic post (identity/
    status, no id/ts/repo/project) and a courier message (id/ts/repo/
    project, no identity/status). Both must fold without error; the topic
    post is the sole source of the session's identity.

    File mtime, not any embedded `ts` field, is what `_fold_sessions()`
    folds on (see sidebar.py's `_fold_sessions` docstring) — this test sets
    mtimes explicitly so the topic-post fixture is the mtime-latest of the
    two, which is what makes the outcome deterministic regardless of
    filesystem iteration order: whichever envelope is mtime-latest supplies
    its own `identity` key directly, so once it is the fixture that
    explicitly carries `identity`, the fold always lands on that value."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.project_dir = Path(self._tmp.name) / "projects" / "kaukea.orchids"
        self.project_dir.mkdir(parents=True)

    def test_topic_post_and_courier_message_fold_together_without_crashing(self) -> None:
        courier_path = self.project_dir / "event_courier_message_content.json"
        topic_path = self.project_dir / "event_topic_post_status.json"
        courier_path.write_text(_load_fixture("event_courier_message_content.json"), encoding="utf-8")
        topic_path.write_text(_load_fixture("event_topic_post_status.json"), encoding="utf-8")
        base = 1_700_000_000.0
        os.utime(courier_path, (base, base))
        os.utime(topic_path, (base + 1, base + 1))  # mtime-latest of the two

        sessions = sidebar._fold_sessions(self.project_dir)

        self.assertEqual(len(sessions), 1, f"expected one folded session, got {sessions!r}")
        rec = sessions["1e6b83cc-f7b1-4010-a66a-6be5951d21aa"]
        self.assertEqual(rec.get("identity"), {"agent": "gardener"})
        self.assertNotIn("id", rec)
        self.assertNotIn("ts", rec)


class LiveSessionLivenessFixtureTests(unittest.TestCase):
    """`event_topic_post_status.json` (see EventEnvelopeFixtureTests above
    for its provenance) is a real captured `orchard:agent:status` post with
    no accompanying lifecycle event -- the literal shape a live session
    takes once its own "started" lifecycle event has aged out of the
    archiver's retention while the session keeps posting (live-session
    liveness bug fix, 2026-07-26). Installed as the sole event for its
    session, it must read "working" (carrying its activity) inside
    ACTIVE_WINDOW_SECONDS of its own file mtime, and "stale" past it."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.projects_root = Path(self._tmp.name) / "projects"
        project_dir = self.projects_root / "kaukea.orchids"
        project_dir.mkdir(parents=True)
        self.event_path = project_dir / "event_topic_post_status.json"
        self.event_path.write_text(
            _load_fixture("event_topic_post_status.json"), encoding="utf-8",
        )
        self.event_mtime = 1_700_000_000.0
        os.utime(self.event_path, (self.event_mtime, self.event_mtime))

    def test_status_post_with_no_lifecycle_event_reads_working_inside_the_window(self) -> None:
        fleet = sidebar.build_model(root=self.projects_root, now=self.event_mtime + 100)
        repo = fleet.repos[0]
        self.assertEqual(repo.status, "working")
        self.assertEqual(repo.activity, "folding")

    def test_status_post_with_no_lifecycle_event_reads_stale_outside_the_window(self) -> None:
        fleet = sidebar.build_model(
            root=self.projects_root,
            now=self.event_mtime + sidebar.ACTIVE_WINDOW_SECONDS + 100,
        )
        repo = fleet.repos[0]
        self.assertEqual(repo.status, "stale")


class CourierOnlyTransportHookFixtureTests(unittest.TestCase):
    """hooks/courier-only-transport.sh against the literal `agent_type`
    values captured live from the PreToolUse harness during this feature:
    a non-courier agent's Bash call carries `agent_type: "sower"`; a
    courier subagent's carries `agent_type: "courier"`."""

    def _run(self, payload: dict) -> subprocess.CompletedProcess:
        return subprocess.run(
            [_HOOK], input=json.dumps(payload), capture_output=True, text=True,
            check=False,
        )

    def _is_deny(self, result: subprocess.CompletedProcess) -> bool:
        if not result.stdout.strip():
            return False
        out = json.loads(result.stdout)
        return out.get("hookSpecificOutput", {}).get("permissionDecision") == "deny"

    def test_captured_sower_agent_type_is_denied_posting_on_the_transport(self) -> None:
        payload = _load_fixture_json("pretooluse_sower_transport_post.json")
        self.assertEqual(payload["agent_type"], "sower")
        result = self._run(payload)
        self.assertEqual(result.returncode, 0)
        self.assertTrue(self._is_deny(result), f"expected deny, got: {result.stdout!r}")

    def test_captured_courier_agent_type_is_allowed_posting_on_the_transport(self) -> None:
        payload = _load_fixture_json("pretooluse_courier_transport_post.json")
        self.assertEqual(payload["agent_type"], "courier")
        result = self._run(payload)
        self.assertEqual(result.returncode, 0)
        self.assertFalse(self._is_deny(result), f"expected allow, got: {result.stdout!r}")


if __name__ == "__main__":
    unittest.main()
