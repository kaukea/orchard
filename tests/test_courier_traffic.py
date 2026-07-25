"""CLI-level tests for `courier.py validate` and the WIRE GRAMMAR v1 traffic
contract (docs/TODO.md.d/bus-message-specifying.md step 6, feature's agreed
test method): each role's emulated session, driven through the real CLI into
a sandboxed courier root, must produce traffic that validates with zero
violations; a set of hand-written envelopes must be flagged exactly as the
spec describes.
"""
import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

_TOOLS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools",
)
if _TOOLS_DIR not in sys.path:
    sys.path.insert(0, _TOOLS_DIR)

from support import courier_root_of, envelope, make_repo, write_message  # noqa: E402

_COURIER_PY = os.path.join(_TOOLS_DIR, "courier.py")


def _poll_for_question_id(folder: Path, deadline: float) -> str | None:
    """Non-destructive read of `folder` for a broadcast question — unlike
    `courier.py receive`, this never deletes, so the role's earlier traffic
    stays on disk for the validate pass at the end of the test."""
    while time.time() < deadline:
        for f in sorted(folder.glob("*.json")):
            if f.name.startswith("."):
                continue
            try:
                env = json.loads(f.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            if env.get("question_id"):
                return env["question_id"]
        time.sleep(0.05)
    return None


class RoleTrafficCliTests(unittest.TestCase):
    """One emulated session per role, driving its contract-specified
    sequence through the real courier.py CLI, then auditing the resulting
    sandbox with `courier.py validate`."""

    PEER = "watcher"

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.repo = make_repo(self._tmp.name)
        self.sandbox_root = courier_root_of(self.repo)
        self._courier("init", self.PEER)

    def _courier(self, *args, session_id=None, check=True):
        env = dict(os.environ)
        if session_id:
            env["CLAUDE_CODE_SESSION_ID"] = session_id
        return subprocess.run(
            [sys.executable, _COURIER_PY, *args],
            cwd=self.repo, capture_output=True, text=True, env=env, check=check,
        )

    def _broadcast(self, session_id: str, body: str) -> None:
        self._courier("broadcast", "--from", session_id, "--body", body, session_id=session_id)

    def _validate(self):
        return subprocess.run(
            [sys.executable, _COURIER_PY, "validate", str(self.sandbox_root)],
            capture_output=True, text=True,
        )

    def assertTrafficIsClean(self) -> None:
        proc = self._validate()
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("0 violation(s)", proc.stdout, proc.stdout)

    def _ask_and_answer(self, session_id: str, question: str, options: list[str],
                         reply_body: str) -> None:
        option_args = []
        for option in options:
            option_args += ["--option", option]
        proc = subprocess.Popen(
            [sys.executable, _COURIER_PY, "ask", "--question", question, *option_args,
             "--poll-interval", "0.05"],
            cwd=self.repo, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
            env=dict(os.environ, CLAUDE_CODE_SESSION_ID=session_id),
        )
        try:
            question_id = _poll_for_question_id(self.sandbox_root / self.PEER, time.time() + 5)
            self.assertIsNotNone(question_id, "ask() never broadcast a question")
            self._courier(
                "send", "--from", self.PEER, "--to", session_id,
                "--in-reply-to", question_id, "--body", reply_body, session_id=self.PEER,
            )
            _stdout, stderr = proc.communicate(timeout=5)
        finally:
            if proc.poll() is None:
                proc.kill()
                proc.communicate()
        self.assertEqual(proc.returncode, 0, stderr)

    def test_orchestrator_role_traffic_validates(self):
        session = "orchestrator1"
        self._courier("announce", session_id=session)
        for body in (
            "orchid:status:triaging",
            "orchid:status:prioritising",
            "orchid:phase:ideation",
            "orchid:subagent:queue:groomer",
            "orchid:subagent:start:groomer",
            "orchid:subagent:done:groomer",
            "orchid:status:dispatching",
        ):
            self._broadcast(session, body)
        self._courier("depart", session_id=session)
        self.assertTrafficIsClean()

    def test_architect_role_traffic_validates(self):
        session = "architect1"
        for body in (
            "orchid:status:discovering",
            "orchid:phase:designing",
            "orchid:status:planning",
            *(f"orchid:phase:building:{k}/6" for k in range(1, 7)),
            "orchid:status:writing",
            "orchid:update:drafted the failing test first",
        ):
            self._broadcast(session, body)
        self._ask_and_answer(
            session, "Proceed with the plan?", ["Yes", "No"],
            '{"index": 0, "option": "Yes"}',
        )
        self._courier("signal", "--state", "done", "--notify-user", session_id=session)
        self._courier("signal", "--state", "finished", session_id=session)
        self.assertTrafficIsClean()

    def test_groomer_role_traffic_validates(self):
        session = "groomer1"
        for body in ("orchid:status:reading", "orchid:phase:scoping", "orchid:status:tending"):
            self._broadcast(session, body)
        self.assertTrafficIsClean()

    def test_bloomer_role_traffic_validates(self):
        session = "bloomer1"
        for body in ("orchid:status:measuring", "orchid:phase:scoping:1/3", "orchid:status:sifting"):
            self._broadcast(session, body)
        self.assertTrafficIsClean()


class TrafficValidateNegativeTests(unittest.TestCase):
    """Hand-written envelopes dropped straight into the spool, bypassing the
    CLI's send-time enforcement — validate is the only backstop for traffic
    that reached disk some other way (sidecar improvisation, a future
    non-courier.py sender)."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.sandbox_root = Path(self._tmp.name)

    def _write(self, env: dict) -> None:
        write_message(self.sandbox_root, "watcher", env)

    def _validate(self):
        return subprocess.run(
            [sys.executable, _COURIER_PY, "validate", str(self.sandbox_root)],
            capture_output=True, text=True,
        )

    def test_native_prompt_broadcast_with_notify_is_one_violation(self):
        self._write(envelope(
            "neg-a", "sidecar1", to="*",
            body="awaiting operator (native prompt)", notify_user=True,
        ))
        proc = self._validate()
        self.assertNotEqual(proc.returncode, 0)
        self.assertEqual(proc.stdout.count("VIOLATION"), 1, proc.stdout)

    def test_legacy_activity_body_is_a_violation(self):
        self._write(envelope("neg-b", "legacyagent", to="*", body="orchid:activity:Closing"))
        proc = self._validate()
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("VIOLATION", proc.stdout)

    def test_directed_free_prose_is_not_flagged(self):
        self._write(envelope("neg-c", "peerX", to="architect1", body="heads up, almost done"))
        proc = self._validate()
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertNotIn("VIOLATION", proc.stdout)
        self.assertNotIn("WARNING", proc.stdout)


if __name__ == "__main__":
    unittest.main()
