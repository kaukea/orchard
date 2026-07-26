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
