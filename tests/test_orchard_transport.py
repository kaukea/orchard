"""Unit tests for the orchard transport in tools/courier.py (the
`:session:`/`:topic:` addressed flat+marker layout under
`$XDG_RUNTIME_DIR/orchard/`, courier.py lines ~802-1246) — distinct from the
legacy per-agent-folder courier tested in tests/test_courier.py.

Every test isolates the environment fully:
  - XDG_RUNTIME_DIR -> a private temp dir (orchard_root()/courier.orchard_root)
  - XDG_CACHE_HOME  -> a private temp dir (orchard_compact archive root)
  - HOME            -> a private temp dir, which is how ORCHARD_REGISTRY_PATH
                        (Path.home() / ".config" / "orchids" /
                        "sidebar-registry.json") is controlled: Path.home()
                        honours $HOME on POSIX, and courier.py never reads
                        XDG_CONFIG_HOME for this path.
so nothing here ever touches the operator's real ~/.config or ~/.cache.

Invocation matches tests/test_courier.py: subprocess against tools/courier.py,
a real git-init'd temp repo per session (tests/support.make_repo), and
CLAUDE_CODE_SESSION_ID pinned per call.

Runs under both `python3 -m unittest discover` and `pytest`.
"""
import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
import zipfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

_TOOLS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools",
)
if _TOOLS_DIR not in sys.path:
    sys.path.insert(0, _TOOLS_DIR)

import courier  # noqa: E402
import orchard_compact  # noqa: E402

from support import make_repo  # noqa: E402

_COURIER_PY = os.path.join(_TOOLS_DIR, "courier.py")


def _env(session_id: str, runtime_dir: Path, cache_home: Path, home: Path) -> dict:
    env = dict(os.environ)
    env["CLAUDE_CODE_SESSION_ID"] = session_id
    env["XDG_RUNTIME_DIR"] = str(runtime_dir)
    env["XDG_CACHE_HOME"] = str(cache_home)
    env["HOME"] = str(home)
    # so a direct `python -c "import courier"` probe (used to learn a repo's
    # project slug without re-deriving the algorithm) resolves the module.
    env["PYTHONPATH"] = _TOOLS_DIR
    return env


def _project_slug(repo: str, env: dict) -> str:
    """Ask courier.project_slug() itself, from within `repo`, rather than
    re-deriving the <repo>.<project> / basename-fallback algorithm here."""
    proc = subprocess.run(
        [sys.executable, "-c", "import courier; print(courier.project_slug())"],
        cwd=repo, capture_output=True, text=True, env=env, check=True,
    )
    return proc.stdout.strip()


def _write_registry(home: Path, slugs) -> None:
    cfg_dir = Path(home) / ".config" / "orchids"
    cfg_dir.mkdir(parents=True, exist_ok=True)
    (cfg_dir / "sidebar-registry.json").write_text(
        json.dumps(list(slugs)), encoding="utf-8",
    )


class _OrchardTestCase(unittest.TestCase):
    """Common env isolation shared by every orchard-transport test below."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        base = Path(self._tmp.name)
        self.runtime_dir = base / "run"
        self.runtime_dir.mkdir()
        self.cache_home = base / "cache"
        self.cache_home.mkdir()
        self.home = base / "home"
        self.home.mkdir()

    def _env(self, session_id: str) -> dict:
        return _env(session_id, self.runtime_dir, self.cache_home, self.home)

    def _courier(self, repo: str, session_id: str, *args):
        return subprocess.run(
            [sys.executable, _COURIER_PY, *args],
            cwd=repo, capture_output=True, text=True, env=self._env(session_id),
        )

    def _slug(self, repo: str) -> str:
        return _project_slug(repo, self._env("slug-probe"))

    def _allow(self, *slugs: str) -> None:
        _write_registry(self.home, slugs)


class CrossRepoOrchardSessionTests(_OrchardTestCase):
    """The assured acceptance scenario: two independent git repos, two
    sessions, sharing ONE XDG_RUNTIME_DIR. Session B learns of session A's
    message purely by calling `receive` in its own repo/session — no git or
    filesystem polling of A's side is involved — and only once B's project
    slug is on the registry allowlist; absent that, the send is denied."""

    def setUp(self) -> None:
        super().setUp()
        root = str(Path(self._tmp.name))
        self.repo_a = make_repo(root)
        self.repo_b = make_repo(root)

    def test_session_a_message_reaches_session_b_across_repos_via_receive_alone(self):
        slug_b = self._slug(self.repo_b)
        self._allow(slug_b)

        send = self._courier(
            self.repo_a, "sessA",
            "send", "--to", ":session:sessB",
            "--subject", "orchard:agent:message:content",
            "--body", "hello from A", "--target-project", slug_b,
        )
        self.assertEqual(send.returncode, 0, send.stderr)

        recv = self._courier(self.repo_b, "sessB", "receive")
        self.assertEqual(recv.returncode, 0, recv.stderr)
        messages = json.loads(recv.stdout)

        self.assertEqual(len(messages), 1)
        msg = messages[0]
        self.assertEqual(msg["from"], ":session:sessA")
        self.assertEqual(msg["to"], ":session:sessB")
        self.assertEqual(msg["subject"], "orchard:agent:message:content")
        self.assertEqual(msg["body"], "hello from A")

    def test_cross_project_send_denied_with_no_registry_present(self):
        send = self._courier(
            self.repo_a, "sessA",
            "send", "--to", ":session:sessB",
            "--subject", "orchard:agent:message:content",
            "--body", "hi", "--target-project", "some-unlisted-project",
        )
        self.assertNotEqual(send.returncode, 0)
        self.assertIn("denied", send.stderr)

        recv = self._courier(self.repo_b, "sessB", "receive")
        self.assertEqual(json.loads(recv.stdout), [])

    def test_cross_project_send_denied_when_registry_omits_target_slug(self):
        slug_b = self._slug(self.repo_b)
        self._allow("some-other-project-entirely")

        send = self._courier(
            self.repo_a, "sessA",
            "send", "--to", ":session:sessB",
            "--subject", "orchard:agent:message:content",
            "--body", "hi", "--target-project", slug_b,
        )
        self.assertNotEqual(send.returncode, 0)
        self.assertIn("denied", send.stderr)


class SameProjectSessionRoundTripTests(_OrchardTestCase):
    """A `:session:` send within the same project round-trips through
    `receive`, and is delete-on-read: a second `receive` finds nothing."""

    def setUp(self) -> None:
        super().setUp()
        self.repo = make_repo(str(Path(self._tmp.name)))

    def test_session_send_receive_round_trips_then_second_receive_is_empty(self):
        send = self._courier(
            self.repo, "sessX",
            "send", "--to", ":session:sessY",
            "--subject", "orchard:agent:message:content", "--body", "ping",
        )
        self.assertEqual(send.returncode, 0, send.stderr)

        first = self._courier(self.repo, "sessY", "receive")
        messages = json.loads(first.stdout)
        self.assertEqual(len(messages), 1)
        self.assertEqual(messages[0]["from"], ":session:sessX")
        self.assertEqual(messages[0]["subject"], "orchard:agent:message:content")
        self.assertEqual(messages[0]["body"], "ping")

        second = self._courier(self.repo, "sessY", "receive")
        self.assertEqual(json.loads(second.stdout), [])


class SubjectVocabularyTests(_OrchardTestCase):
    """A `--subject` outside the closed orchard wire-grammar set is rejected;
    a valid one is accepted."""

    def setUp(self) -> None:
        super().setUp()
        self.repo = make_repo(str(Path(self._tmp.name)))

    def test_valid_subject_is_accepted(self):
        proc = self._courier(
            self.repo, "sessV",
            "send", "--to", ":session:peer", "--subject", "orchard:agent:status",
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)

    def test_off_list_subject_is_rejected(self):
        proc = self._courier(
            self.repo, "sessV",
            "send", "--to", ":session:peer", "--subject", "orchard:agent:bogus",
        )
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("unknown orchard subject", proc.stderr)


class LivenessMarkerTests(_OrchardTestCase):
    """orchard_deliver() touches/creates `<sid>.marker` and bumps the parent
    project dir's own mtime on every write (nested writes don't bubble
    automatically), which is what a liveness watcher polls."""

    def setUp(self) -> None:
        super().setUp()
        self.repo = make_repo(str(Path(self._tmp.name)))

    def test_marker_created_and_parent_project_dir_mtime_advances(self):
        slug = self._slug(self.repo)
        project_path = self.runtime_dir / "orchard" / "projects" / slug
        project_path.mkdir(parents=True)
        old = time.time() - 3600
        os.utime(project_path, (old, old))
        before_mtime = project_path.stat().st_mtime

        send = self._courier(
            self.repo, "sessSrc",
            "send", "--to", ":session:sessTarget",
            "--subject", "orchard:agent:message:content", "--body", "hi",
        )
        self.assertEqual(send.returncode, 0, send.stderr)

        marker = project_path / "sessTarget.marker"
        self.assertTrue(marker.exists())
        after_mtime = project_path.stat().st_mtime
        self.assertGreater(after_mtime, before_mtime)


class FeatureMarkerTests(_OrchardTestCase):
    """`orchard_deliver()` merges a durable `<feature-id>.marker` node
    alongside the per-session heartbeat marker whenever the envelope's
    `identity` carries a `feature`. The marker stays keyed on the FEATURE
    at file level (`feature`, `name` — the feature's own display name,
    `area`, `updated`); it persists the TASKS that feature maps to as a
    `tasks[]` list, each entry keyed by `task` (never `feature` — a
    feature spans many tasks in general, so keying a task entry on its
    feature would conflate the two levels) and carrying its own
    `name`/`state`/`updated` — never agent/session identity (role,
    name-of-agent, parent, per-session state), which is ephemeral and
    disappears with the agent. `tasks` stays a list so sibling tasks under
    one feature node can persist even though, in this repo, a feature
    currently maps to a single task. The per-session `<sid>.marker`
    heartbeat keeps working unchanged (covered by LivenessMarkerTests);
    this class covers only the new node.
    """

    def setUp(self) -> None:
        super().setUp()
        self.project_dir = self.runtime_dir / "orchard" / "projects" / "own.repo"
        self.project_dir.mkdir(parents=True)

    def _envelope(self, subject: str, *, feature="feat-x", agent="landscaper",
                  feature_name="Feat X", task=None, task_name=None,
                  parent=None, body=None) -> dict:
        env = {"from": ":session:sessA", "subject": subject,
               "identity": {"feature": feature, "agent": agent,
                             "feature_name": feature_name, "task": task,
                             "task_name": task_name, "parent": parent}}
        if body is not None:
            env["body"] = body
        return env

    def _marker(self, feature="feat-x") -> dict:
        return json.loads((self.project_dir / f"{feature}.marker").read_text())

    def test_no_feature_marker_written_without_identity_feature(self):
        courier.orchard_deliver(self.project_dir, "sessA",
                                 {"from": ":session:sessA",
                                  "subject": "orchard:agent:status", "body": "hi"})
        self.assertEqual(list(self.project_dir.glob("*.marker")),
                          [self.project_dir / "sessA.marker"])

    def test_feature_marker_created_with_task_shape(self):
        courier.orchard_deliver(self.project_dir, "sessA",
                                 self._envelope("orchard:agent:lifecycle:starting"))
        marker = self._marker()
        self.assertEqual(marker["schema"], 2)
        self.assertEqual(marker["project"], "own.repo")
        self.assertEqual(marker["feature"], "feat-x")
        self.assertEqual(marker["name"], "Feat X")
        self.assertIsNone(marker["area"])
        self.assertNotIn("sessions", marker)
        self.assertEqual(len(marker["tasks"]), 1)
        task = marker["tasks"][0]
        # today one feature maps to exactly one task, so with no distinct
        # ORCHID_TASK_ID the task id defaults to the feature id itself
        self.assertEqual(task["task"], "feat-x")
        self.assertEqual(task["name"], "Feat X")
        self.assertNotIn("feature", task)
        self.assertNotIn("area", task)
        self.assertEqual(task["state"], "working")
        self.assertIn("updated", task)
        self.assertIn("updated", marker)

    def test_no_agent_identity_is_retained_for_display(self):
        courier.orchard_deliver(self.project_dir, "sessA",
                                 self._envelope("orchard:agent:lifecycle:starting"))
        raw = (self.project_dir / "feat-x.marker").read_text()
        self.assertNotIn("landscaper", raw)
        self.assertNotIn("sessA", raw)

    def test_outcome_sets_terminal_task_state(self):
        courier.orchard_deliver(self.project_dir, "sessA",
                                 self._envelope("orchard:agent:lifecycle:starting"))
        courier.orchard_deliver(self.project_dir, "sessA",
                                 self._envelope("orchard:agent:outcome:fail"))
        marker = self._marker()
        self.assertEqual(len(marker["tasks"]), 1)
        self.assertEqual(marker["tasks"][0]["state"], "failed")

    def test_completed_task_persists_in_the_marker(self):
        courier.orchard_deliver(self.project_dir, "sessA",
                                 self._envelope("orchard:agent:lifecycle:starting"))
        courier.orchard_deliver(self.project_dir, "sessA",
                                 self._envelope("orchard:agent:outcome:success"))
        marker = self._marker()
        self.assertEqual(len(marker["tasks"]), 1)
        self.assertEqual(marker["tasks"][0]["state"], "done")

        courier.orchard_deliver(self.project_dir, "sessA",
                                 self._envelope("orchard:agent:status"))
        marker = self._marker()
        self.assertEqual(len(marker["tasks"]), 1)
        self.assertEqual(marker["tasks"][0]["state"], "done")

    def test_delegation_traffic_does_not_change_task_state(self):
        courier.orchard_deliver(self.project_dir, "sessA",
                                 self._envelope("orchard:agent:lifecycle:starting"))
        courier.orchard_deliver(
            self.project_dir, "sessA",
            self._envelope("orchard:agent:delegation:begin", body={"subagent": "sub-1"}))
        marker = self._marker()
        self.assertEqual(len(marker["tasks"]), 1)
        self.assertEqual(marker["tasks"][0]["state"], "working")
        self.assertNotIn("label", marker["tasks"][0])

        courier.orchard_deliver(
            self.project_dir, "sessB",
            self._envelope("orchard:agent:delegation:end", agent="sower",
                            body={"subagent": "sub-1"}))
        marker = self._marker()
        self.assertEqual(len(marker["tasks"]), 1)
        self.assertEqual(marker["tasks"][0]["state"], "working")
        self.assertNotIn("sessions", marker)

    def test_second_delivery_merges_rather_than_truncates(self):
        courier.orchard_deliver(self.project_dir, "sessA",
                                 self._envelope("orchard:agent:lifecycle:starting"))
        first_updated = self._marker()["updated"]

        courier.orchard_deliver(self.project_dir, "sessA",
                                 self._envelope("orchard:agent:status"))
        marker = self._marker()
        self.assertGreaterEqual(marker["updated"], first_updated)
        self.assertEqual(len(marker["tasks"]), 1)
        self.assertEqual(marker["tasks"][0]["name"], "Feat X")

    def test_topic_delivery_never_writes_a_feature_marker(self):
        topic_dir = self.runtime_dir / "orchard" / "topics" / "repository/own.repo"
        courier.orchard_deliver(topic_dir, "sessA",
                                 self._envelope("orchard:agent:lifecycle:starting"))
        self.assertEqual(list(topic_dir.glob("*.marker")),
                          [topic_dir / "sessA.marker"])

    def test_merge_strips_legacy_shapes_but_keeps_current_task_entries(self):
        # A marker written by earlier, now-rejected code: a `sessions`
        # identity cache, a `tasks[]` entry with no `task` key at all (a
        # delegation label), and a schema-1 entry keyed by the now-retired
        # `feature` field — none of these are the CURRENT (`task`-keyed)
        # shape, so merge-never-truncate discards all three rather than
        # crash on them. A genuinely current entry, for a DIFFERENT task
        # under this same feature, is carried forward untouched — proving
        # merge-never-truncate still holds for the shape that matters.
        (self.project_dir / "feat-x.marker").write_text(json.dumps({
            "schema": 1, "project": "own.repo", "feature": "feat-x",
            "sessions": {"s1": {"agent": "architect", "state": "done"}},
            "tasks": [
                {"label": "verify-task-persist", "state": "done", "updated": "t0"},
                {"feature": "feat-x", "name": "Feat X (schema 1)", "area": None,
                 "state": "done", "updated": "t0"},
                {"task": "feat-x-step-0", "name": "Step 0", "state": "done",
                 "updated": "t0"},
            ],
            "updated": "t0",
        }), encoding="utf-8")

        courier.orchard_deliver(self.project_dir, "sessA",
                                 self._envelope("orchard:agent:lifecycle:starting"))

        marker = self._marker()
        self.assertNotIn("sessions", marker)
        self.assertEqual(
            {t["task"] for t in marker["tasks"]}, {"feat-x", "feat-x-step-0"},
        )
        survivor = next(t for t in marker["tasks"] if t["task"] == "feat-x-step-0")
        self.assertEqual(survivor["state"], "done")
        self.assertEqual(survivor["name"], "Step 0")


class SignalPrefixTests(_OrchardTestCase):
    """`signal --to` is documented as a bare session id, but every other
    `--to` in this script takes a full `:session:<id>` address — a caller
    that follows that habit here used to double the prefix
    (`:session::session:<id>`) once cmd_signal wrapped it again, leaking a
    `:` into the delivered marker filename (Decision-091 forbids that
    outright). Both the bare-id (documented) and already-prefixed shape
    must land on the same, single-prefixed result."""

    def setUp(self) -> None:
        super().setUp()
        self.repo = make_repo(str(Path(self._tmp.name)))

    def _signal(self, to_value: str):
        return self._courier(
            self.repo, "sessSignaller",
            "signal", "--state", "finished", "--to", to_value,
        )

    def _project_dir(self):
        return self.runtime_dir / "orchard" / "projects" / self._slug(self.repo)

    def test_bare_to_is_not_doubled(self):
        proc = self._signal("parentSess")
        self.assertEqual(proc.returncode, 0, proc.stderr)

        project_dir = self._project_dir()
        self.assertTrue((project_dir / "parentSess.marker").exists())
        self.assertEqual(list(project_dir.glob("*:*")), [])

    def test_already_prefixed_to_is_not_doubled(self):
        proc = self._signal(":session:parentSess")
        self.assertEqual(proc.returncode, 0, proc.stderr)

        project_dir = self._project_dir()
        self.assertTrue((project_dir / "parentSess.marker").exists())
        self.assertEqual(list(project_dir.glob("*:*")), [])

        files = list(project_dir.glob("parentSess.*.json"))
        self.assertEqual(len(files), 1)
        envelope = json.loads(files[0].read_text(encoding="utf-8"))
        self.assertEqual(envelope["to"], ":session:parentSess")


class OrchardFilenameValidationTests(unittest.TestCase):
    """Decision-091's closed set of orchard filename shapes —
    `<sessionid>.<ts>.json`, `<sessionid>.marker`, `<feature-id>.marker` —
    enforced by validate_orchard_filename(), the single gate write_orchard_file()
    calls before anything touches disk. No coercion, no silent repair:
    anything outside the closed set raises."""

    def test_valid_shapes_are_accepted(self):
        courier.validate_orchard_filename("sess1.2026-07-26T14-04-13.469488.json")
        courier.validate_orchard_filename("sess1.marker")
        courier.validate_orchard_filename("feat-x.marker")

    def test_routing_prefix_in_any_component_is_rejected(self):
        with self.assertRaises(ValueError):
            courier.validate_orchard_filename(":session:sess1.marker")
        with self.assertRaises(ValueError):
            courier.validate_orchard_filename(":session:sess1.2026-07-26T14-04-13.469488.json")

    def test_missing_json_extension_is_rejected(self):
        with self.assertRaises(ValueError):
            courier.validate_orchard_filename("sess1.2026-07-26T14-04-13.469488")

    def test_write_orchard_file_rejects_rather_than_repairs_a_malformed_name(self):
        with tempfile.TemporaryDirectory() as d:
            dir_path = Path(d)
            with self.assertRaises(ValueError):
                courier.write_orchard_file(dir_path, "sess1.2026-07-26T14-04-13.469488", {"x": 1})
            self.assertEqual(list(dir_path.iterdir()), [])


class RequestReplyTests(_OrchardTestCase):
    """`request` blocks until a matching `reply` (matched on in_reply_to)
    arrives, then prints the reply body. The reply is sent from a second
    "responder" session once it has, itself, learned the request's id purely
    via `receive` — no shared in-process state."""

    def setUp(self) -> None:
        super().setUp()
        self.repo = make_repo(str(Path(self._tmp.name)))

    def test_request_blocks_until_reply_then_prints_it(self):
        proc = subprocess.Popen(
            [sys.executable, _COURIER_PY, "request", "--to", ":session:responder",
             "--subject", "orchard:agent:message:request", "--body", "ping"],
            cwd=self.repo, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
            env=self._env("requester"),
        )
        try:
            request_id = None
            deadline = time.time() + 5
            while time.time() < deadline and request_id is None:
                recv = self._courier(self.repo, "responder", "receive")
                for m in json.loads(recv.stdout):
                    if m.get("subject") == "orchard:agent:message:request":
                        request_id = m["id"]
                if request_id is None:
                    time.sleep(0.05)
            self.assertIsNotNone(request_id, "request never reached responder's mailbox")

            reply = self._courier(
                self.repo, "responder",
                "reply", "--to", ":session:requester", "--in-reply-to", request_id,
                "--subject", "orchard:agent:message:response", "--body", "pong",
            )
            self.assertEqual(reply.returncode, 0, reply.stderr)

            stdout, stderr = proc.communicate(timeout=10)
        finally:
            if proc.poll() is None:      # pragma: no cover - only on a genuine hang
                proc.kill()
                proc.communicate()

        self.assertEqual(proc.returncode, 0, stderr)
        self.assertEqual(stdout.strip(), "pong")


class CompactionTests(_OrchardTestCase):
    """orchard_compact.compact_now() sweeps a project dir directly: a
    message older than COMPACT_AGE_SECONDS (default 7200s / 120min) is moved
    into a persistent zip under XDG_CACHE_HOME and removed from the live
    dir; a recent message and any `.marker` are left untouched."""

    def setUp(self) -> None:
        super().setUp()
        self.repo = make_repo(str(Path(self._tmp.name)))

    def test_stale_message_archived_recent_message_and_marker_survive(self):
        slug = self._slug(self.repo)
        project_path = self.runtime_dir / "orchard" / "projects" / slug
        project_path.mkdir(parents=True)

        now = datetime.now(timezone.utc)
        old_ts = (now - timedelta(minutes=150)).strftime("%Y-%m-%dT%H-%M-%S.%f")
        recent_ts = (now - timedelta(minutes=5)).strftime("%Y-%m-%dT%H-%M-%S.%f")

        old_file = project_path / f"sessOld.{old_ts}.json"
        old_file.write_text(json.dumps({
            "id": "old1", "ts": now.isoformat(), "from": ":session:x",
            "to": ":session:sessOld", "subject": "orchard:agent:status",
        }), encoding="utf-8")

        recent_file = project_path / f"sessRecent.{recent_ts}.json"
        recent_file.write_text(json.dumps({
            "id": "recent1", "ts": now.isoformat(), "from": ":session:x",
            "to": ":session:sessRecent", "subject": "orchard:agent:status",
        }), encoding="utf-8")

        marker = project_path / "sessRecent.marker"
        marker.touch()

        with mock.patch.dict(os.environ, {"XDG_CACHE_HOME": str(self.cache_home)}):
            orchard_compact.compact_now(project_path)

        self.assertFalse(old_file.exists())
        self.assertTrue(recent_file.exists())
        self.assertTrue(marker.exists())

        archive_dir = self.cache_home / "orchard" / "archives"
        zips = list(archive_dir.glob("*.zip"))
        self.assertEqual(len(zips), 1)
        with zipfile.ZipFile(zips[0]) as zf:
            names = zf.namelist()
            self.assertTrue(any(old_file.name in n for n in names))
            self.assertFalse(any(recent_file.name in n for n in names))


if __name__ == "__main__":
    unittest.main()
