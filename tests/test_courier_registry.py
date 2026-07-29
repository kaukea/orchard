"""Unit + CLI tests for the courier's name registry and NAME addressing
(docs/courier-wire.md, "Addressing by NAME — ruled 2026-07-29"; Decision-121,
Decision-130, Decision-132).

Covers: an entry appears on `init`; it disappears when its OWN
`orchard:agent:lifecycle:stopped` passes through the transport; a stale
entry (dead marker mtime) reads as not-live without needing that event;
resolve_name()'s nearest-first tiering; same-level clash fan-out to every
live holder; the undeliverable-name error; and the outside-tree subject
restriction on `send --to <name>`.

Runs under both `python3 -m unittest discover` and `pytest`.
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

import courier  # noqa: E402

from support import make_repo  # noqa: E402

_COURIER_PY = os.path.join(_TOOLS_DIR, "courier.py")


def _git(repo, *args):
    subprocess.run(["git", "-C", repo, *args], check=True, capture_output=True, text=True)


def _repo_on_branch(base: Path, branch: str, remote: str) -> str:
    """A git repo with one commit, checked out on `branch`, carrying `remote`
    as its origin — so project_slug()'s repo-prefix half matches across
    several such repos regardless of their temp-dir basenames, and its
    branch half is exactly `branch` (not the "detached" fallback an
    unborn/commit-less repo would produce)."""
    repo = make_repo(str(base))
    _git(repo, "symbolic-ref", "HEAD", f"refs/heads/{branch}")
    _git(repo, "config", "user.email", "t@t.t")
    _git(repo, "config", "user.name", "t")
    _git(repo, "remote", "add", "origin", remote)
    _git(repo, "commit", "--allow-empty", "-m", "init")
    return repo


class RegistryCliTestCase(unittest.TestCase):
    """Shared fixture: one XDG_RUNTIME_DIR (registry is machine-scoped, not
    per-worktree — matches production) and a helper repo builder."""

    REMOTE = "git@example.com:acme/widget.git"

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.base = Path(self._tmp.name)
        self.runtime_dir = self.base / "run"
        self.runtime_dir.mkdir()
        self.cache_home = self.base / "cache"
        self.cache_home.mkdir()
        self.home = self.base / "home"
        self.home.mkdir()

    def _env(self, session_id, repo=None, agent=None, **extra):
        env = {k: v for k, v in os.environ.items()
               if k not in ("CLAUDE_CODE_AGENT", "ORCHID_PARENT_SESSION", "ORCHID_PARENT_PROJECT")}
        env.update(
            CLAUDE_CODE_SESSION_ID=session_id,
            XDG_RUNTIME_DIR=str(self.runtime_dir), XDG_CACHE_HOME=str(self.cache_home),
            HOME=str(self.home),
        )
        if agent is not None:
            env["CLAUDE_CODE_AGENT"] = agent
        env.update(extra)
        return env

    def _courier(self, repo, session_id, *args, agent=None, check=False, **extra_env):
        return subprocess.run(
            [sys.executable, _COURIER_PY, *args],
            cwd=repo, capture_output=True, text=True,
            env=self._env(session_id, agent=agent, **extra_env), check=check,
        )

    def _registry_file(self, session_id):
        return self.runtime_dir / "orchard" / "registry" / f"{session_id}.json"


class InitRegistrationTests(RegistryCliTestCase):
    def test_init_with_agent_role_writes_registry_entry(self):
        repo = _repo_on_branch(self.base, "f/mine", self.REMOTE)
        proc = self._courier(repo, "sowerA", "init", agent="sower", check=True)
        self.assertTrue(proc.returncode == 0)

        entry = json.loads(self._registry_file("sowerA").read_text(encoding="utf-8"))
        self.assertEqual(entry["name"], "sower")
        self.assertEqual(entry["session_id"], "sowerA")
        self.assertTrue(entry["project_slug"].startswith("acme.widget@"))
        self.assertIn("mailbox_dir", entry)
        self.assertIn("started_ts", entry)

    def test_init_without_agent_role_registers_nothing(self):
        repo = _repo_on_branch(self.base, "f/mine", self.REMOTE)
        self._courier(repo, "noRoleA", "init", agent=None, check=True)
        self.assertFalse(self._registry_file("noRoleA").exists())


class RemovalOnStoppedTests(RegistryCliTestCase):
    def test_own_lifecycle_stopped_deregisters_the_sender(self):
        repo = _repo_on_branch(self.base, "f/mine", self.REMOTE)
        self._courier(repo, "sowerB", "init", agent="sower", check=True)
        self.assertTrue(self._registry_file("sowerB").exists())

        proc = self._courier(
            repo, "sowerB", "send", "--to", ":session:someoneElse",
            "--subject", "orchard:agent:lifecycle:stopped", agent="sower",
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertFalse(self._registry_file("sowerB").exists())

    def test_lifecycle_stopped_never_removes_a_different_sender(self):
        repo = _repo_on_branch(self.base, "f/mine", self.REMOTE)
        self._courier(repo, "sowerC", "init", agent="sower", check=True)
        self._courier(repo, "sowerD", "init", agent="sower", check=True)

        self._courier(
            repo, "sowerC", "send", "--to", ":session:someoneElse",
            "--subject", "orchard:agent:lifecycle:stopped", agent="sower",
        )
        self.assertFalse(self._registry_file("sowerC").exists())
        self.assertTrue(self._registry_file("sowerD").exists())


class StaleGuardTests(RegistryCliTestCase):
    def test_stale_entry_is_excluded_from_live_entries_and_resolution(self):
        repo = _repo_on_branch(self.base, "f/mine", self.REMOTE)
        with mock.patch.dict(os.environ, {
            "XDG_RUNTIME_DIR": str(self.runtime_dir),
            "CLAUDE_CODE_SESSION_ID": "staleSowerA",
        }, clear=False):
            path = courier.name_registry_path("staleSowerA")
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps({
                "name": "sower", "session_id": "staleSowerA",
                "project_slug": "acme.widget@f-mine",
                "mailbox_dir": "/does/not/matter", "started_ts": "2026-01-01T00:00:00+00:00",
            }), encoding="utf-8")
            stale_time = time.time() - courier.NAME_REGISTRY_STALE_SECONDS - 60
            os.utime(path, (stale_time, stale_time))

            live = courier.live_name_registry_entries()
            self.assertEqual(live, [])

            with mock.patch("courier.project_slug", return_value="acme.widget@f-mine"):
                self.assertEqual(courier.resolve_name("sower"), [])


class ResolutionOrderUnitTests(unittest.TestCase):
    """Pure unit-level: tiering is exercised directly against hand-written
    registry entries, monkeypatching project_slug() rather than spinning up
    several real worktrees for what is a pure data-shape decision."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.runtime_dir = Path(self._tmp.name) / "run"
        self.runtime_dir.mkdir()
        self._env_patch = mock.patch.dict(os.environ, {"XDG_RUNTIME_DIR": str(self.runtime_dir)})
        self._env_patch.start()
        self.addCleanup(self._env_patch.stop)
        self.own_slug = "acme.widget@f-mine"
        self.other_worktree_slug = "acme.widget@f-other"
        self.main_slug = "acme.widget@main"

    def _write_entry(self, sid, name, slug):
        path = courier.name_registry_path(sid)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({
            "name": name, "session_id": sid, "project_slug": slug,
            "mailbox_dir": "/x", "started_ts": "2026-01-01T00:00:00+00:00",
        }), encoding="utf-8")

    def test_own_project_wins_over_other_worktree_and_main(self):
        self._write_entry("ownHolder", "sower", self.own_slug)
        self._write_entry("otherHolder", "sower", self.other_worktree_slug)
        self._write_entry("mainHolder", "sower", self.main_slug)
        with mock.patch("courier.project_slug", return_value=self.own_slug):
            result = courier.resolve_name("sower")
        self.assertEqual([e["session_id"] for e in result], ["ownHolder"])

    def test_falls_back_to_other_worktree_when_own_project_has_no_holder(self):
        self._write_entry("otherHolder", "sower", self.other_worktree_slug)
        self._write_entry("mainHolder", "sower", self.main_slug)
        with mock.patch("courier.project_slug", return_value=self.own_slug):
            result = courier.resolve_name("sower")
        self.assertEqual([e["session_id"] for e in result], ["otherHolder"])

    def test_falls_back_to_main_when_only_main_has_a_holder(self):
        self._write_entry("mainHolder", "sower", self.main_slug)
        with mock.patch("courier.project_slug", return_value=self.own_slug):
            result = courier.resolve_name("sower")
        self.assertEqual([e["session_id"] for e in result], ["mainHolder"])

    def test_different_repo_is_never_a_candidate(self):
        self._write_entry("otherRepoHolder", "sower", "other.repo@main")
        with mock.patch("courier.project_slug", return_value=self.own_slug):
            result = courier.resolve_name("sower")
        self.assertEqual(result, [])

    def test_unknown_name_resolves_to_nothing(self):
        self._write_entry("ownHolder", "sower", self.own_slug)
        with mock.patch("courier.project_slug", return_value=self.own_slug):
            result = courier.resolve_name("landscaper")
        self.assertEqual(result, [])


class ClashFanoutTests(RegistryCliTestCase):
    def test_same_level_clash_delivers_to_every_live_holder(self):
        repo = _repo_on_branch(self.base, "f/mine", self.REMOTE)
        self._courier(repo, "sowerE", "init", agent="sower", check=True)
        self._courier(repo, "sowerF", "init", agent="sower", check=True)

        proc = self._courier(
            repo, "landscaperA", "send", "--to", "sower",
            "--subject", "orchard:agent:message:content", "--body", "hi", agent="landscaper",
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("delivered to 2 live holder(s)", proc.stdout)

        received_e = json.loads(
            self._courier(repo, "sowerE", "receive", agent="sower", check=True).stdout
        )
        received_f = json.loads(
            self._courier(repo, "sowerF", "receive", agent="sower", check=True).stdout
        )
        self.assertEqual(len(received_e), 1)
        self.assertEqual(len(received_f), 1)
        self.assertEqual(received_e[0]["from"], ":session:landscaperA")
        self.assertEqual(received_f[0]["from"], ":session:landscaperA")


class DeadNameErrorTests(RegistryCliTestCase):
    def test_send_to_a_name_nobody_holds_is_undeliverable(self):
        repo = _repo_on_branch(self.base, "f/mine", self.REMOTE)
        proc = self._courier(
            repo, "landscaperB", "send", "--to", "nosuchname",
            "--subject", "orchard:agent:message:content", "--body", "hi", agent="landscaper",
        )
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("undeliverable", proc.stderr)
        self.assertIn("nosuchname", proc.stderr)

    def test_every_holder_stopped_is_also_undeliverable(self):
        repo = _repo_on_branch(self.base, "f/mine", self.REMOTE)
        self._courier(repo, "sowerG", "init", agent="sower", check=True)
        self._courier(
            repo, "sowerG", "send", "--to", ":session:someoneElse",
            "--subject", "orchard:agent:lifecycle:stopped", agent="sower",
        )
        proc = self._courier(
            repo, "landscaperC", "send", "--to", "sower",
            "--subject", "orchard:agent:message:content", "--body", "hi", agent="landscaper",
        )
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("undeliverable", proc.stderr)


class OutsideTreeEnforcementTests(RegistryCliTestCase):
    """A name that resolves outside the sender's own tree (main, when the
    sender is on a different worktree of the same repo) may only be reached
    with a question/status-query subject (Decision-132)."""

    def test_ordinary_content_send_across_a_tree_boundary_is_refused(self):
        main_repo = _repo_on_branch(self.base, "main", self.REMOTE)
        own_repo = _repo_on_branch(self.base, "f/mine", self.REMOTE)
        self._courier(main_repo, "mainSower", "init", agent="sower", check=True)

        proc = self._courier(
            own_repo, "landscaperD", "send", "--to", "sower",
            "--subject", "orchard:agent:message:content", "--body", "hi", agent="landscaper",
        )
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("outside your own tree", proc.stderr)

    def test_a_question_subject_may_cross_the_boundary(self):
        main_repo = _repo_on_branch(self.base, "main", self.REMOTE)
        own_repo = _repo_on_branch(self.base, "f/mine", self.REMOTE)
        self._courier(main_repo, "mainSowerB", "init", agent="sower", check=True)

        proc = self._courier(
            own_repo, "landscaperE", "send", "--to", "sower",
            "--subject", "orchard:agent:message:request", "--body", "status?", agent="landscaper",
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("delivered to 1 live holder(s)", proc.stdout)


if __name__ == "__main__":
    unittest.main()
