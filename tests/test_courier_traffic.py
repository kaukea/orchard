"""CLI-level tests for `courier.py validate` and the WIRE GRAMMAR v1 traffic
contract (docs/TODO.md.d/bus-message-specifying.md step 6, feature's agreed
test method).

`broadcast` (the fan-out courier.py used to offer role traffic) is retired —
see tests/test_courier.py's OrchidGrammarCliTests for that. The roles' real
traffic now goes through `orchard_topic.py post status/lifecycle/...`
(telemetry, never fanned out) and directed `courier.py send`/`request --to
:session:<id>`; RoleTrafficCliTests below drives each role's traffic through
the real CLIs into a sandboxed orchard root and audits it with `courier.py
validate`, exactly as the retired broadcast-based version did.
TrafficValidateNegativeTests is unaffected by the retirement — it exercises
`validate` directly against hand-written envelopes.
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

from support import envelope, make_repo, write_message  # noqa: E402

_COURIER_PY = os.path.join(_TOOLS_DIR, "courier.py")
_ORCHARD_TOPIC_PY = os.path.join(_TOOLS_DIR, "orchard_topic.py")


class RoleTrafficCliTests(unittest.TestCase):
    """One emulated session per role, driving its status/lifecycle chatter
    through the real `orchard_topic.py post` CLI (the sanctioned telemetry
    writer — never a fan-out), plus one shared directed-traffic test for
    `send`/`request --to :session:<id>`, then auditing the resulting
    sandbox with `courier.py validate`."""

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
        self.repo = make_repo(str(base))

    def _env(self, session_id):
        return dict(
            os.environ, CLAUDE_CODE_SESSION_ID=session_id,
            XDG_RUNTIME_DIR=str(self.runtime_dir), XDG_CACHE_HOME=str(self.cache_home),
            HOME=str(self.home),
        )

    def _topic_post(self, session_id: str, *args):
        return subprocess.run(
            [sys.executable, _ORCHARD_TOPIC_PY, "post", *args],
            cwd=self.repo, capture_output=True, text=True, env=self._env(session_id),
        )

    def _courier(self, session_id, *args):
        return subprocess.run(
            [sys.executable, _COURIER_PY, *args],
            cwd=self.repo, capture_output=True, text=True, env=self._env(session_id),
        )

    def _slug(self):
        proc = subprocess.run(
            [sys.executable, "-c", "import courier; print(courier.project_slug())"],
            cwd=self.repo, capture_output=True, text=True,
            env=dict(self._env("slug-probe"), PYTHONPATH=_TOOLS_DIR), check=True,
        )
        return proc.stdout.strip()

    def _orchard_root(self) -> Path:
        return self.runtime_dir / "orchard"

    def _validate(self):
        return subprocess.run(
            [sys.executable, _COURIER_PY, "validate", str(self._orchard_root())],
            capture_output=True, text=True,
        )

    def assertTrafficIsClean(self) -> None:
        proc = self._validate()
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("0 violation(s)", proc.stdout, proc.stdout)

    def _role_topic_traffic(self, session: str, *status_words: str) -> None:
        start = self._topic_post(session, "lifecycle", "starting")
        self.assertEqual(start.returncode, 0, start.stderr)
        for words in status_words:
            proc = self._topic_post(session, "status", words)
            self.assertEqual(proc.returncode, 0, proc.stderr)
        stop = self._topic_post(session, "lifecycle", "stopped")
        self.assertEqual(stop.returncode, 0, stop.stderr)

    def test_orchestrator_role_topic_traffic_validates(self):
        self._role_topic_traffic("orchestrator1", "triaging", "prioritising", "dispatching")
        self.assertTrafficIsClean()

    def test_architect_role_topic_traffic_validates(self):
        self._role_topic_traffic("architect1", "discovering", "planning", "writing tests")
        self.assertTrafficIsClean()

    def test_groomer_role_topic_traffic_validates(self):
        self._role_topic_traffic("groomer1", "reading", "tending")
        self.assertTrafficIsClean()

    def test_bloomer_role_topic_traffic_validates(self):
        self._role_topic_traffic("bloomer1", "measuring", "sifting")
        self.assertTrafficIsClean()

    def test_directed_send_and_request_reply_traffic_validates(self):
        requester, responder = "architect2", "watcher"

        send = self._courier(
            requester, "send", "--to", f":session:{responder}",
            "--subject", "orchard:agent:message:content", "--body", "drafted the plan",
        )
        self.assertEqual(send.returncode, 0, send.stderr)

        proc = subprocess.Popen(
            [sys.executable, _COURIER_PY, "request", "--to", f":session:{responder}",
             "--subject", "orchard:agent:message:request", "--body", "proceed with the plan?"],
            cwd=self.repo, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
            env=self._env(requester),
        )
        try:
            project_path = self._orchard_root() / "projects" / self._slug()
            deadline = time.time() + 5
            request_id = None
            while time.time() < deadline and request_id is None:
                if project_path.is_dir():
                    for f in sorted(project_path.glob(f"{responder}.*.json")):
                        if f.name.startswith("."):
                            continue
                        try:
                            env = json.loads(f.read_text(encoding="utf-8"))
                        except (OSError, json.JSONDecodeError):
                            continue
                        if env.get("subject") == "orchard:agent:message:request":
                            request_id = env["id"]
                            break
                if request_id is None:
                    time.sleep(0.05)
            self.assertIsNotNone(request_id, "request never reached the responder's mailbox")

            reply = self._courier(
                responder, "reply", "--to", f":session:{requester}",
                "--in-reply-to", request_id, "--subject", "orchard:agent:message:response",
                "--body", "yes",
            )
            self.assertEqual(reply.returncode, 0, reply.stderr)

            stdout, stderr = proc.communicate(timeout=10)
        finally:
            if proc.poll() is None:
                proc.kill()
                proc.communicate()
        self.assertEqual(proc.returncode, 0, stderr)
        self.assertEqual(stdout.strip(), "yes")

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
